"""
Scraper runner — orchestrates scraping, deduplication, and DB persistence.
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from backend.models import Restaurant
from backend.scraper.overpass import search_restaurants as osm_search
from backend.config import get_settings
from rich.console import Console

console = Console()


async def run_scrape(
    db: AsyncSession,
    city: str,
    cuisine: str = "",
    country: str = "US",
    source: str = "openstreetmap",
    max_results: int = 60,
) -> dict:
    """
    Scrape restaurants, deduplicate against DB, and insert new records.
    Returns a summary dict.
    """
    console.print(f"[bold cyan]Scraping {source}[/] — {cuisine or 'all'} restaurants in {city}, {country}")

    if source == "openstreetmap":
        raw = await osm_search(city=city, cuisine=cuisine, country=country, max_results=max_results)

    elif source == "google":
        settings = get_settings()
        if not settings.google_places_api_key:
            raise ValueError("GOOGLE_PLACES_API_KEY is not set in .env")
        from backend.scraper.google_places import search_restaurants as google_search, get_place_details
        raw = await google_search(city=city, cuisine=cuisine, country=country, max_results=max_results)

    elif source == "yelp":
        settings = get_settings()
        if not settings.yelp_api_key:
            raise ValueError("YELP_API_KEY is not set in .env")
        from backend.scraper.yelp import search_restaurants as yelp_search
        raw = await yelp_search(city=city, cuisine=cuisine, country=country, max_results=max_results)

    else:
        raise ValueError(f"Unknown source: {source}")

    inserted = 0
    skipped = 0

    for place in raw:
        if await _find_existing(db, place):
            skipped += 1
            continue

        # For Google, fetch full details (phone, website, coords)
        if source == "google" and place.get("google_place_id"):
            try:
                from backend.scraper.google_places import get_place_details
                details = await get_place_details(place["google_place_id"])
                place.update({k: v for k, v in details.items() if v is not None})
            except Exception as e:
                console.print(f"[yellow]Details fetch failed for {place.get('name')}: {e}[/]")

        db.add(Restaurant(
            name=place.get("name", "Unknown"),
            address=place.get("address"),
            city=place.get("city") or city,
            country=place.get("country") or country,
            lat=place.get("lat"),
            lng=place.get("lng"),
            cuisine_raw=place.get("cuisine_raw"),
            rating=place.get("rating"),
            price_level=place.get("price_level"),
            phone=place.get("phone"),
            website=place.get("website"),
            google_place_id=place.get("google_place_id"),
            yelp_id=place.get("yelp_id"),
            source=place.get("source"),
        ))
        inserted += 1

    await db.commit()
    summary = {"scraped": len(raw), "inserted": inserted, "skipped": skipped}
    console.print(f"[green]Done:[/] {summary}")
    return summary


async def _find_existing(db: AsyncSession, place: dict) -> bool:
    """Dedup by OSM id, google_place_id, yelp_id, or exact name+city match."""
    osm_id = place.get("osm_id")
    gid = place.get("google_place_id")
    yid = place.get("yelp_id")
    name = place.get("name")
    city = place.get("city")

    filters = []
    if gid:
        filters.append(Restaurant.google_place_id == gid)
    if yid:
        filters.append(Restaurant.yelp_id == yid)
    # For OSM we store source+name+city as dedup key
    if osm_id and name and city:
        filters.append(
            (Restaurant.source == "openstreetmap") &
            (Restaurant.name == name) &
            (Restaurant.city == city)
        )

    if not filters:
        return False

    result = await db.execute(select(Restaurant).where(or_(*filters)))
    return result.scalar_one_or_none() is not None
