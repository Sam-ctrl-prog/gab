"""
Google Places API scraper.
Finds restaurants by city + cuisine type, returns structured data.
"""
import httpx
from typing import Optional
from backend.config import get_settings

PLACES_BASE = "https://maps.googleapis.com/maps/api/place"


async def search_restaurants(
    city: str,
    cuisine: str = "",
    country: str = "US",
    max_results: int = 60,
) -> list[dict]:
    """
    Search Google Places for restaurants matching city + cuisine.
    Returns a list of raw place dicts.
    """
    settings = get_settings()
    api_key = settings.google_places_api_key
    if not api_key:
        raise ValueError("GOOGLE_PLACES_API_KEY is not set in .env")

    query = f"{cuisine} restaurant {city} {country}".strip()
    results: list[dict] = []
    next_page_token: Optional[str] = None

    async with httpx.AsyncClient(timeout=15) as client:
        while len(results) < max_results:
            params: dict = {
                "query": query,
                "type": "restaurant",
                "key": api_key,
            }
            if next_page_token:
                params = {"pagetoken": next_page_token, "key": api_key}

            resp = await client.get(f"{PLACES_BASE}/textsearch/json", params=params)
            resp.raise_for_status()
            data = resp.json()

            for place in data.get("results", []):
                results.append(_parse_place(place))
                if len(results) >= max_results:
                    break

            next_page_token = data.get("next_page_token")
            if not next_page_token:
                break

            # Google requires a short delay before using next_page_token
            import asyncio
            await asyncio.sleep(2)

    return results


async def get_place_details(place_id: str) -> dict:
    """Fetch full details for a single place (phone, website, opening hours)."""
    settings = get_settings()
    fields = "name,formatted_address,formatted_phone_number,website,url,rating,price_level,geometry"

    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(
            f"{PLACES_BASE}/details/json",
            params={"place_id": place_id, "fields": fields, "key": settings.google_places_api_key},
        )
        resp.raise_for_status()
        result = resp.json().get("result", {})

    return {
        "google_place_id": place_id,
        "name": result.get("name"),
        "address": result.get("formatted_address"),
        "phone": result.get("formatted_phone_number"),
        "website": result.get("website"),
        "rating": result.get("rating"),
        "price_level": result.get("price_level"),
        "lat": result.get("geometry", {}).get("location", {}).get("lat"),
        "lng": result.get("geometry", {}).get("location", {}).get("lng"),
        "source": "google",
    }


def _parse_place(place: dict) -> dict:
    loc = place.get("geometry", {}).get("location", {})
    return {
        "google_place_id": place.get("place_id"),
        "name": place.get("name"),
        "address": place.get("formatted_address"),
        "rating": place.get("rating"),
        "price_level": place.get("price_level"),
        "lat": loc.get("lat"),
        "lng": loc.get("lng"),
        "cuisine_raw": ", ".join(place.get("types", [])),
        "source": "google",
    }
