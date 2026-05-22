"""
Batch menu seeder — fetches menus for all restaurants that have a website
but no menu ingested yet. Tries menu_url first, then common menu paths on
the restaurant website. Auto-runs cuisine matching after each successful ingest.
"""
import asyncio
from urllib.parse import urljoin, urlparse
import httpx
from bs4 import BeautifulSoup
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from backend.models import Restaurant, Menu
from backend.knowledge.menu_kb import _extract_text, _create_menu
from backend.knowledge.cuisine_kb import match_menu_to_cuisine
from rich.console import Console

console = Console()

# Common paths to try when looking for a menu page
MENU_PATHS = [
    "/menu", "/menus", "/food", "/our-menu", "/the-menu",
    "/food-menu", "/dining", "/eat", "/what-we-serve",
]

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; GAB-MenuBot/1.0)"}
TIMEOUT = 15
MIN_TEXT_LENGTH = 200   # skip pages with too little content
MENU_KEYWORDS = ["appetizer", "entree", "entrée", "dessert", "starter", "main course",
                 "beverage", "cocktail", "wine", "beer", "salad", "soup", "pasta",
                 "burger", "sandwich", "pizza", "sushi", "ramen", "curry", "noodle",
                 "breakfast", "lunch", "dinner", "brunch", "small plate", "large plate"]


async def _fetch_url(client: httpx.AsyncClient, url: str) -> str | None:
    """Fetch a URL and return cleaned text, or None on failure."""
    try:
        resp = await client.get(url, headers=HEADERS, timeout=TIMEOUT, follow_redirects=True)
        if resp.status_code != 200:
            return None
        ct = resp.headers.get("content-type", "")
        if "html" not in ct:
            return None
        return _extract_text(resp.text)
    except Exception:
        return None


def _looks_like_menu(text: str) -> bool:
    """Heuristic: does this page look like it contains menu content?"""
    if len(text) < MIN_TEXT_LENGTH:
        return False
    text_lower = text.lower()
    hits = sum(1 for kw in MENU_KEYWORDS if kw in text_lower)
    return hits >= 3


async def _find_menu_text(client: httpx.AsyncClient, website: str, menu_url: str | None) -> tuple[str | None, str | None]:
    """
    Returns (text, source_url) — the best menu text we could find.
    Priority: menu_url > common menu paths > homepage.
    """
    base = website.rstrip("/")

    # 1. Explicit menu_url
    if menu_url:
        text = await _fetch_url(client, menu_url)
        if text and _looks_like_menu(text):
            return text, menu_url

    # 2. Try common menu paths
    for path in MENU_PATHS:
        url = base + path
        text = await _fetch_url(client, url)
        if text and _looks_like_menu(text):
            return text, url
        await asyncio.sleep(0.3)

    # 3. Try to find a menu link on the homepage
    try:
        resp = await client.get(base, headers=HEADERS, timeout=TIMEOUT, follow_redirects=True)
        if resp.status_code == 200 and "html" in resp.headers.get("content-type", ""):
            soup = BeautifulSoup(resp.text, "lxml")
            for a in soup.find_all("a", href=True):
                href = a["href"].lower()
                text_content = a.get_text().lower()
                if any(kw in href or kw in text_content for kw in ["menu", "food", "eat", "dining"]):
                    full_url = urljoin(base, a["href"])
                    # Stay on same domain
                    if urlparse(full_url).netloc == urlparse(base).netloc:
                        page_text = await _fetch_url(client, full_url)
                        if page_text and _looks_like_menu(page_text):
                            return page_text, full_url
                        await asyncio.sleep(0.3)
    except Exception:
        pass

    # 4. Fallback: use homepage if it has enough content
    text = await _fetch_url(client, base)
    if text and _looks_like_menu(text):
        return text, base

    return None, None


async def seed_menus(db: AsyncSession) -> dict:
    """
    For every restaurant with a website and no menu yet, try to scrape a menu.
    Auto-runs cuisine matching after each successful ingest.
    """
    # Find restaurants that have a website but no menu ingested
    subq = select(Menu.restaurant_id).distinct()
    q = (
        select(Restaurant)
        .where(
            Restaurant.website.is_not(None),
            Restaurant.id.not_in(subq),
        )
        .order_by(Restaurant.rating.desc().nulls_last())
    )
    result = await db.execute(q)
    restaurants = result.scalars().all()

    total = len(restaurants)
    ingested = 0
    matched = 0
    failed = 0

    console.print(f"[cyan]Found {total} restaurants with websites but no menu[/]")

    async with httpx.AsyncClient() as client:
        for i, r in enumerate(restaurants):
            console.print(f"[dim][{i+1}/{total}][/] {r.name} — {r.website}")
            try:
                text, source_url = await _find_menu_text(client, r.website, r.menu_url)
                if not text:
                    console.print(f"  [yellow]No menu found[/]")
                    failed += 1
                    await asyncio.sleep(1)
                    continue

                menu = await _create_menu(db, r.id, text, source_url=source_url, source_type="url")
                ingested += 1
                console.print(f"  [green]Ingested {len(menu.items if hasattr(menu, 'items') else [])} items — {source_url}[/]")

                # Auto cuisine match
                try:
                    await match_menu_to_cuisine(db, menu.id)
                    matched += 1
                except Exception as e:
                    console.print(f"  [yellow]Match failed: {e}[/]")

                await asyncio.sleep(2)   # be polite to restaurant websites

            except Exception as e:
                console.print(f"  [red]Error: {e}[/]")
                failed += 1
                await asyncio.sleep(1)

    summary = {
        "total_candidates": total,
        "menus_ingested": ingested,
        "cuisine_matched": matched,
        "failed": failed,
    }
    console.print(f"[bold green]Menu seed complete:[/] {summary}")
    return summary
