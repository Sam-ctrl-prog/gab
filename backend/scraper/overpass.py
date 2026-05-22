"""
OpenStreetMap / Overpass API scraper — completely free, no API key needed.
Uses Nominatim to geocode the city, then Overpass to pull restaurants.
"""
import httpx
import asyncio

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
OVERPASS_URL = "https://overpass-api.de/api/interpreter"
HEADERS = {"User-Agent": "GAB-DiningClub/1.0 (dining club app)"}


async def geocode_city(city: str, country: str = "US") -> tuple[float, float, float, float]:
    """Return (south, west, north, east) bounding box for a city."""
    async with httpx.AsyncClient(timeout=15, headers=HEADERS) as client:
        resp = await client.get(NOMINATIM_URL, params={
            "q": f"{city}, {country}",
            "format": "json",
            "limit": 1,
        })
        resp.raise_for_status()
        results = resp.json()

    if not results:
        raise ValueError(f"Could not geocode city: {city}, {country}")

    bb = results[0].get("boundingbox")
    if bb:
        return float(bb[0]), float(bb[2]), float(bb[1]), float(bb[3])  # S, W, N, E

    # Fallback: build box from lat/lon with ~0.15 degree radius
    lat = float(results[0]["lat"])
    lon = float(results[0]["lon"])
    return lat - 0.15, lon - 0.2, lat + 0.15, lon + 0.2


async def search_restaurants(
    city: str,
    cuisine: str = "",
    country: str = "US",
    max_results: int = 60,
) -> list[dict]:
    """Query Overpass for restaurants in a city, optionally filtered by cuisine tag."""
    south, west, north, east = await geocode_city(city, country)
    bbox = f"{south},{west},{north},{east}"

    # Build cuisine filter if provided
    cuisine_filter = _cuisine_to_osm_tag(cuisine)
    if cuisine_filter:
        node_query = f'node["amenity"="restaurant"][{cuisine_filter}]({bbox});'
        way_query  = f'way["amenity"="restaurant"][{cuisine_filter}]({bbox});'
    else:
        node_query = f'node["amenity"="restaurant"]["name"]({bbox});'
        way_query  = f'way["amenity"="restaurant"]["name"]({bbox});'

    overpass_ql = f"""
[out:json][timeout:40];
(
  {node_query}
  {way_query}
);
out center body {max_results};
"""

    async with httpx.AsyncClient(timeout=45, headers=HEADERS) as client:
        resp = await client.post(OVERPASS_URL, data={"data": overpass_ql})
        resp.raise_for_status()
        data = resp.json()

    results = []
    for element in data.get("elements", []):
        parsed = _parse_element(element, city, country)
        if parsed:
            results.append(parsed)
        if len(results) >= max_results:
            break

    return results


def _parse_element(el: dict, city: str, country: str) -> dict | None:
    tags = el.get("tags", {})
    name = tags.get("name")
    if not name:
        return None

    # Coordinates — nodes have lat/lon directly, ways have center
    if el.get("type") == "node":
        lat = el.get("lat")
        lng = el.get("lon")
    else:
        center = el.get("center", {})
        lat = center.get("lat")
        lng = center.get("lon")

    # Build address
    addr_parts = [
        tags.get("addr:housenumber", ""),
        tags.get("addr:street", ""),
    ]
    address = " ".join(p for p in addr_parts if p).strip()
    if not address:
        address = tags.get("addr:full", "")

    # Cuisine tag → raw string
    cuisine_raw = tags.get("cuisine", "").replace(";", ", ").replace("_", " ").title()

    return {
        "name": name,
        "address": address or None,
        "city": tags.get("addr:city") or city,
        "country": tags.get("addr:country") or country,
        "lat": lat,
        "lng": lng,
        "cuisine_raw": cuisine_raw or None,
        "phone": tags.get("phone") or tags.get("contact:phone"),
        "website": tags.get("website") or tags.get("contact:website"),
        "source": "openstreetmap",
        "osm_id": str(el.get("id")),
    }


# Map common cuisine search terms → OSM cuisine tag values
_CUISINE_MAP = {
    "thai": '"cuisine"~"thai"',
    "italian": '"cuisine"~"italian"',
    "japanese": '"cuisine"~"japanese|sushi|ramen"',
    "chinese": '"cuisine"~"chinese"',
    "mexican": '"cuisine"~"mexican"',
    "indian": '"cuisine"~"indian"',
    "french": '"cuisine"~"french"',
    "korean": '"cuisine"~"korean"',
    "vietnamese": '"cuisine"~"vietnamese"',
    "american": '"cuisine"~"american|burger"',
    "mediterranean": '"cuisine"~"mediterranean|greek"',
    "pizza": '"cuisine"~"pizza|italian"',
    "sushi": '"cuisine"~"sushi|japanese"',
    "ramen": '"cuisine"~"ramen|japanese"',
    "seafood": '"cuisine"~"seafood"',
    "bbq": '"cuisine"~"barbecue|bbq"',
    "middle eastern": '"cuisine"~"middle_eastern|lebanese|turkish"',
    "ethiopian": '"cuisine"~"ethiopian|african"',
    "peruvian": '"cuisine"~"peruvian|latin_american"',
    "spanish": '"cuisine"~"spanish|tapas"',
}


def _cuisine_to_osm_tag(cuisine: str) -> str:
    if not cuisine:
        return ""
    key = cuisine.lower().strip()
    # Exact match first
    if key in _CUISINE_MAP:
        return _CUISINE_MAP[key]
    # Partial match
    for k, v in _CUISINE_MAP.items():
        if key in k or k in key:
            return v
    # Fallback: use raw value as regex
    safe = cuisine.replace('"', "").replace("'", "")
    return f'"cuisine"~"{safe}"'
