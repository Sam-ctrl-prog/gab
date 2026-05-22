"""
Menu knowledge base.
Handles ingestion (URL scrape / PDF / manual text), item parsing,
embedding generation, and semantic search.
"""
import json
import re
from typing import Optional
import httpx
from bs4 import BeautifulSoup
from openai import AsyncOpenAI
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from backend.models import Menu, MenuItem, Restaurant
from backend.config import get_settings

EMBED_MODEL = "text-embedding-3-small"
CHAT_MODEL = "gpt-4o-mini"


def _client() -> AsyncOpenAI:
    return AsyncOpenAI(api_key=get_settings().openai_api_key)


# ─── Ingestion ───────────────────────────────────────────────────────────────

async def ingest_from_url(db: AsyncSession, restaurant_id: int, url: str) -> Menu:
    """Scrape a menu URL, parse items, embed, and store."""
    async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
        resp = await client.get(url, headers={"User-Agent": "Mozilla/5.0"})
        resp.raise_for_status()
        html = resp.text

    text = _extract_text(html)
    return await _create_menu(db, restaurant_id, text, source_url=url, source_type="url")


async def ingest_from_text(db: AsyncSession, restaurant_id: int, text: str) -> Menu:
    """Ingest a menu from raw pasted text."""
    return await _create_menu(db, restaurant_id, text, source_type="manual")


async def _create_menu(
    db: AsyncSession,
    restaurant_id: int,
    raw_text: str,
    source_url: str = None,
    source_type: str = "manual",
) -> Menu:
    items_data = await _parse_menu_items(raw_text)

    menu = Menu(
        restaurant_id=restaurant_id,
        source_url=source_url,
        source_type=source_type,
        raw_text=raw_text,
    )
    db.add(menu)
    await db.flush()  # get menu.id

    for item in items_data:
        text_for_embed = f"{item['name']} {item.get('description', '')}".strip()
        embedding = await _embed(text_for_embed)
        db.add(MenuItem(
            menu_id=menu.id,
            name=item["name"],
            description=item.get("description"),
            price=item.get("price"),
            category=item.get("category"),
            embedding=embedding,
        ))

    await db.commit()
    await db.refresh(menu)
    return menu


# ─── Search ──────────────────────────────────────────────────────────────────

async def search_menus(db: AsyncSession, query: str, top_k: int = 10) -> list[dict]:
    """
    Semantic search across all menu items using cosine similarity.
    Returns top_k items with restaurant info.
    """
    query_embedding = await _embed(query)

    result = await db.execute(
        select(MenuItem, Menu, Restaurant)
        .join(Menu, MenuItem.menu_id == Menu.id)
        .join(Restaurant, Menu.restaurant_id == Restaurant.id)
        .where(MenuItem.embedding.is_not(None))
    )
    rows = result.all()

    scored = []
    for item, menu, restaurant in rows:
        if not item.embedding:
            continue
        sim = _cosine_similarity(query_embedding, item.embedding)
        scored.append({
            "score": sim,
            "item_name": item.name,
            "item_description": item.description,
            "item_price": item.price,
            "category": item.category,
            "restaurant_id": restaurant.id,
            "restaurant_name": restaurant.name,
            "restaurant_city": restaurant.city,
        })

    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored[:top_k]


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _extract_text(html: str) -> str:
    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script", "style", "nav", "footer", "header"]):
        tag.decompose()
    return soup.get_text(separator="\n", strip=True)


async def _parse_menu_items(raw_text: str) -> list[dict]:
    """Use GPT to extract structured menu items from raw text."""
    client = _client()
    prompt = (
        "Extract all menu items from the following text. "
        "Return a JSON array where each item has: name, description (optional), price (number, optional), category (optional). "
        "Only return valid JSON, no explanation.\n\n"
        + raw_text[:6000]
    )
    resp = await client.chat.completions.create(
        model=CHAT_MODEL,
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
    )
    content = resp.choices[0].message.content
    try:
        parsed = json.loads(content)
        # Model may return {"items": [...]} or just [...]
        if isinstance(parsed, list):
            return parsed
        for key in ("items", "menu_items", "dishes"):
            if key in parsed and isinstance(parsed[key], list):
                return parsed[key]
    except Exception:
        pass
    return []


async def _embed(text: str) -> list[float]:
    client = _client()
    resp = await client.embeddings.create(model=EMBED_MODEL, input=text[:2000])
    return resp.data[0].embedding


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    if isinstance(b, str):
        b = json.loads(b)
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = sum(x ** 2 for x in a) ** 0.5
    norm_b = sum(x ** 2 for x in b) ** 0.5
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)
