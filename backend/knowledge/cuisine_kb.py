"""
Cuisine knowledge base.
- Seeds 50 cuisine profiles into DB
- Matches a restaurant's menu text to its best-fit cuisine profile using GPT
- Auto-links restaurant.cuisine_id on high-confidence matches
"""
import json
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from openai import AsyncOpenAI
from backend.models import Cuisine, Menu, Restaurant
from backend.knowledge.cuisines_data import CUISINES
from backend.config import get_settings

CHAT_MODEL = "gpt-4o-mini"
AUTO_LINK_THRESHOLD = 70   # confidence % above which we auto-set restaurant.cuisine_id


def _client() -> AsyncOpenAI:
    return AsyncOpenAI(api_key=get_settings().openai_api_key)


# ─── Seeding ─────────────────────────────────────────────────────────────────

async def seed_cuisines(db: AsyncSession) -> int:
    """Insert all 50 cuisine profiles if they don't already exist. Returns count inserted."""
    inserted = 0
    for data in CUISINES:
        existing = await db.execute(select(Cuisine).where(Cuisine.name == data["name"]))
        if existing.scalar_one_or_none():
            continue
        db.add(Cuisine(
            name=data["name"],
            region=data.get("region", ""),
            sub_region=data.get("sub_region"),
            description=data.get("description"),
            key_ingredients=data.get("key_ingredients"),
            key_techniques=data.get("key_techniques"),
            flavor_profile=data.get("flavor_profile"),
            typical_dishes=data.get("typical_dishes"),
            differentiating_factors=data.get("differentiating_factors"),
        ))
        inserted += 1
    await db.commit()
    return inserted


async def reseed_cuisines(db: AsyncSession) -> int:
    """Update existing cuisine profiles with new data (e.g. differentiating_factors). Returns updated count."""
    updated = 0
    for data in CUISINES:
        result = await db.execute(select(Cuisine).where(Cuisine.name == data["name"]))
        c = result.scalar_one_or_none()
        if c:
            c.description = data.get("description", c.description)
            c.key_ingredients = data.get("key_ingredients", c.key_ingredients)
            c.key_techniques = data.get("key_techniques", c.key_techniques)
            c.flavor_profile = data.get("flavor_profile", c.flavor_profile)
            c.typical_dishes = data.get("typical_dishes", c.typical_dishes)
            c.differentiating_factors = data.get("differentiating_factors")
            updated += 1
        else:
            db.add(Cuisine(
                name=data["name"],
                region=data.get("region", ""),
                sub_region=data.get("sub_region"),
                description=data.get("description"),
                key_ingredients=data.get("key_ingredients"),
                key_techniques=data.get("key_techniques"),
                flavor_profile=data.get("flavor_profile"),
                typical_dishes=data.get("typical_dishes"),
                differentiating_factors=data.get("differentiating_factors"),
            ))
            updated += 1
    await db.commit()
    return updated


# ─── Menu-to-Cuisine Matching ─────────────────────────────────────────────────

async def match_menu_to_cuisine(db: AsyncSession, menu_id: int) -> dict:
    """
    Two-pass analysis:
    Pass 1 — lightweight: scan menu text against all cuisine names + dishes to get top 5 candidates.
    Pass 2 — deep: analyze menu vs top 5 with full profiles including differentiating_factors.
    Auto-links restaurant.cuisine_id if top match confidence >= AUTO_LINK_THRESHOLD.
    """
    result = await db.execute(select(Menu).where(Menu.id == menu_id))
    menu = result.scalar_one_or_none()
    if not menu:
        raise ValueError(f"Menu {menu_id} not found")
    if not menu.raw_text:
        raise ValueError("Menu has no raw text to analyze")

    cuisines_result = await db.execute(select(Cuisine))
    all_cuisines = cuisines_result.scalars().all()

    menu_text = menu.raw_text[:4000]

    # ── Pass 1: Narrow to top 5 candidates ───────────────────────────────────
    lightweight_index = [
        {
            "name": c.name,
            "region": c.region,
            "sub_region": c.sub_region or "",
            "typical_dishes": c.typical_dishes or [],
            "key_ingredients": (c.key_ingredients or [])[:5],
        }
        for c in all_cuisines
    ]

    pass1_prompt = f"""You are a culinary expert. Given a restaurant menu, identify the top 5 most likely cuisine profiles from the list below.

Return JSON: {{"candidates": ["CuisineName1", "CuisineName2", "CuisineName3", "CuisineName4", "CuisineName5"]}}
Names must exactly match the list.

CUISINE LIST:
{json.dumps(lightweight_index)}

MENU:
{menu_text[:2000]}
"""

    client = _client()
    pass1_resp = await client.chat.completions.create(
        model=CHAT_MODEL,
        messages=[{"role": "user", "content": pass1_prompt}],
        response_format={"type": "json_object"},
    )

    try:
        candidates_raw = json.loads(pass1_resp.choices[0].message.content)
        candidate_names = candidates_raw.get("candidates", [])[:5]
    except Exception:
        candidate_names = [c.name for c in all_cuisines[:5]]

    # ── Pass 2: Deep analysis against candidates ──────────────────────────────
    candidate_cuisines = [c for c in all_cuisines if c.name in candidate_names]
    # Fallback: include all if narrowing failed
    if not candidate_cuisines:
        candidate_cuisines = all_cuisines

    deep_index = [
        {
            "name": c.name,
            "region": c.region,
            "sub_region": c.sub_region or "",
            "description": c.description or "",
            "key_ingredients": c.key_ingredients or [],
            "key_techniques": c.key_techniques or [],
            "typical_dishes": c.typical_dishes or [],
            "flavor_profile": c.flavor_profile or {},
            "differentiating_factors": c.differentiating_factors or "",
        }
        for c in candidate_cuisines
    ]

    pass2_prompt = f"""You are an expert culinary analyst specializing in identifying cuisine sub-profiles.

Analyze the menu below against these {len(candidate_cuisines)} candidate cuisine profiles.
Pay special attention to the "differentiating_factors" field — it tells you exactly what signals distinguish each cuisine.

For each of the top 3 matches return:
- cuisine_name: must exactly match the profile name
- confidence: 0–100 (be precise — 90+ means unmistakable, 70–89 means strong match, 50–69 means likely, below 50 means possible)
- reasoning: 2–3 sentences citing specific dishes/ingredients from the menu that match
- sub_profile: if applicable (e.g. "Northern Thailand", "Sichuan") — only if clearly evidenced

Return JSON: {{"matches": [{{"cuisine_name": "...", "confidence": 85, "reasoning": "...", "sub_profile": "..."}}]}}

CANDIDATE CUISINE PROFILES:
{json.dumps(deep_index, indent=2)}

FULL MENU TEXT:
{menu_text}
"""

    pass2_resp = await client.chat.completions.create(
        model=CHAT_MODEL,
        messages=[{"role": "user", "content": pass2_prompt}],
        response_format={"type": "json_object"},
    )

    try:
        match_result = json.loads(pass2_resp.choices[0].message.content)
    except Exception:
        match_result = {"matches": [], "error": "parse_failed"}

    # ── Auto-link restaurant to cuisine ──────────────────────────────────────
    matches = match_result.get("matches", [])
    if matches and matches[0].get("confidence", 0) >= AUTO_LINK_THRESHOLD:
        top_name = matches[0]["cuisine_name"]
        cuisine_row = next((c for c in all_cuisines if c.name == top_name), None)
        if cuisine_row and menu.restaurant_id:
            rest_result = await db.execute(
                select(Restaurant).where(Restaurant.id == menu.restaurant_id)
            )
            restaurant = rest_result.scalar_one_or_none()
            if restaurant:
                restaurant.cuisine_id = cuisine_row.id
                match_result["auto_linked"] = {
                    "restaurant_id": restaurant.id,
                    "cuisine_id": cuisine_row.id,
                    "cuisine_name": top_name,
                }

    # Persist result on menu
    menu.cuisine_match = match_result
    await db.commit()

    return match_result


# ─── Batch matching ───────────────────────────────────────────────────────────

async def match_all_unmatched(db: AsyncSession) -> dict:
    """
    Match all menus that haven't been analyzed yet (cuisine_match is NULL).
    Returns summary of how many were processed.
    """
    import asyncio
    result = await db.execute(
        select(Menu).where(Menu.raw_text.is_not(None), Menu.cuisine_match.is_(None))
    )
    unmatched = result.scalars().all()

    processed = 0
    failed = 0
    for menu in unmatched:
        try:
            await match_menu_to_cuisine(db, menu.id)
            processed += 1
            await asyncio.sleep(0.5)   # rate limit buffer
        except Exception:
            failed += 1

    return {"processed": processed, "failed": failed, "total_unmatched": len(unmatched)}


# ─── Search ──────────────────────────────────────────────────────────────────

async def search_cuisines(db: AsyncSession, query: str) -> list[dict]:
    """Text search across cuisine names, regions, and descriptions."""
    query_lower = query.lower()
    result = await db.execute(select(Cuisine))
    cuisines = result.scalars().all()

    matches = []
    for c in cuisines:
        score = 0
        if query_lower in (c.name or "").lower(): score += 10
        if query_lower in (c.region or "").lower(): score += 5
        if query_lower in (c.sub_region or "").lower(): score += 7
        if query_lower in (c.description or "").lower(): score += 3
        if score > 0:
            matches.append({"score": score, "cuisine": _cuisine_to_dict(c)})

    matches.sort(key=lambda x: x["score"], reverse=True)
    return [m["cuisine"] for m in matches]


def _cuisine_to_dict(c: Cuisine) -> dict:
    return {
        "id": c.id,
        "name": c.name,
        "region": c.region,
        "sub_region": c.sub_region,
        "description": c.description,
        "key_ingredients": c.key_ingredients,
        "key_techniques": c.key_techniques,
        "flavor_profile": c.flavor_profile,
        "typical_dishes": c.typical_dishes,
        "differentiating_factors": c.differentiating_factors,
    }
