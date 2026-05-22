"""
Yelp Fusion API scraper — used as fallback or supplement to Google Places.
"""
import httpx
from backend.config import get_settings

YELP_BASE = "https://api.yelp.com/v3"


async def search_restaurants(
    city: str,
    cuisine: str = "",
    country: str = "US",
    max_results: int = 50,
) -> list[dict]:
    settings = get_settings()
    api_key = settings.yelp_api_key
    if not api_key:
        raise ValueError("YELP_API_KEY is not set in .env")

    results: list[dict] = []
    offset = 0
    limit = min(50, max_results)

    headers = {"Authorization": f"Bearer {api_key}"}

    async with httpx.AsyncClient(timeout=15) as client:
        while len(results) < max_results:
            params = {
                "location": f"{city}, {country}",
                "categories": cuisine or "restaurants",
                "limit": limit,
                "offset": offset,
            }
            resp = await client.get(f"{YELP_BASE}/businesses/search", headers=headers, params=params)
            resp.raise_for_status()
            data = resp.json()

            businesses = data.get("businesses", [])
            if not businesses:
                break

            for biz in businesses:
                results.append(_parse_business(biz))
                if len(results) >= max_results:
                    break

            offset += len(businesses)
            if offset >= data.get("total", 0):
                break

    return results


def _parse_business(biz: dict) -> dict:
    coords = biz.get("coordinates", {})
    location = biz.get("location", {})
    address_parts = [
        location.get("address1", ""),
        location.get("city", ""),
        location.get("state", ""),
        location.get("zip_code", ""),
    ]
    categories = [c.get("title", "") for c in biz.get("categories", [])]

    return {
        "yelp_id": biz.get("id"),
        "name": biz.get("name"),
        "address": ", ".join(p for p in address_parts if p),
        "city": location.get("city"),
        "country": location.get("country"),
        "phone": biz.get("display_phone"),
        "website": biz.get("url"),
        "rating": biz.get("rating"),
        "price_level": len(biz.get("price", "") or ""),
        "lat": coords.get("latitude"),
        "lng": coords.get("longitude"),
        "cuisine_raw": ", ".join(categories),
        "source": "yelp",
    }
