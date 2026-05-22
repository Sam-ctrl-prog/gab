"""
Comprehensive NYC restaurant seeder.
Scrapes all 5 boroughs across key cuisine categories from OpenStreetMap.
Designed to be run once (or periodically) from the backend — no UI needed.
"""
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from backend.scraper.runner import run_scrape
from rich.console import Console

console = Console()

# (area_name, osm_search_term, country)
NYC_AREAS = [
    ("Manhattan",     "Manhattan, New York",     "US"),
    ("Brooklyn",      "Brooklyn, New York",      "US"),
    ("Queens",        "Queens, New York",        "US"),
    ("Bronx",         "Bronx, New York",         "US"),
    ("Staten Island", "Staten Island, New York", "US"),
]

# Cuisine passes — each pass targets a specific cuisine across all boroughs.
# Empty string = no filter (all restaurants).
CUISINE_PASSES = [
    "",             # all restaurants (broadest pass)
    "thai",
    "japanese",
    "chinese",
    "italian",
    "mexican",
    "korean",
    "indian",
    "vietnamese",
    "mediterranean",
    "french",
    "american",
    "seafood",
    "middle eastern",
    "ethiopian",
    "peruvian",
    "spanish",
    "bbq",
]

MAX_PER_QUERY = 100   # Overpass result cap per request


async def seed_nyc(db: AsyncSession, areas: list = None, cuisines: list = None) -> dict:
    """
    Run a full NYC scrape across all boroughs and cuisine types.
    Returns aggregate totals.
    """
    areas = areas or NYC_AREAS
    cuisines = cuisines or CUISINE_PASSES

    total_scraped = 0
    total_inserted = 0
    total_skipped = 0
    errors = 0

    for area_name, search_term, country in areas:
        for cuisine in cuisines:
            label = f"{area_name} / {cuisine or 'all'}"
            try:
                console.print(f"[cyan]→ {label}[/]")
                result = await run_scrape(
                    db=db,
                    city=search_term,
                    cuisine=cuisine,
                    country=country,
                    source="openstreetmap",
                    max_results=MAX_PER_QUERY,
                )
                total_scraped += result["scraped"]
                total_inserted += result["inserted"]
                total_skipped += result["skipped"]
                # Brief pause to respect Overpass rate limits
                await asyncio.sleep(1.5)
            except Exception as e:
                console.print(f"[red]Error on {label}: {e}[/]")
                errors += 1
                await asyncio.sleep(2)

    summary = {
        "scraped": total_scraped,
        "inserted": total_inserted,
        "skipped": total_skipped,
        "errors": errors,
    }
    console.print(f"[bold green]NYC seed complete:[/] {summary}")
    return summary
