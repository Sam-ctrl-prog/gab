from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from backend.database import get_db
from backend.models import Cuisine, Restaurant
from backend.knowledge.cuisine_kb import seed_cuisines, reseed_cuisines, search_cuisines

router = APIRouter(prefix="/cuisines", tags=["cuisines"])


@router.get("")
async def list_cuisines(region: str = None, sub_region: str = None, db: AsyncSession = Depends(get_db)):
    q = select(Cuisine).order_by(Cuisine.region, Cuisine.name)
    if region:
        q = q.where(Cuisine.region.ilike(f"%{region}%"))
    if sub_region:
        q = q.where(Cuisine.sub_region.ilike(f"%{sub_region}%"))
    result = await db.execute(q)
    cuisines = result.scalars().all()

    # Get restaurant counts per cuisine in one query
    counts_q = (
        select(Restaurant.cuisine_id, func.count(Restaurant.id).label("cnt"))
        .where(Restaurant.cuisine_id.is_not(None))
        .group_by(Restaurant.cuisine_id)
    )
    counts_result = await db.execute(counts_q)
    counts = {row.cuisine_id: row.cnt for row in counts_result.all()}

    return [_serialize(c, counts.get(c.id, 0)) for c in cuisines]


@router.get("/search")
async def search(query: str, db: AsyncSession = Depends(get_db)):
    return await search_cuisines(db, query)


@router.post("/seed")
async def seed(db: AsyncSession = Depends(get_db)):
    """Seed all 50 cuisine profiles into the database."""
    count = await seed_cuisines(db)
    return {"inserted": count}


@router.post("/reseed")
async def reseed(db: AsyncSession = Depends(get_db)):
    """Update existing cuisine profiles with latest data (differentiating_factors etc)."""
    count = await reseed_cuisines(db)
    return {"updated": count}


@router.get("/{cuisine_id}")
async def get_cuisine(cuisine_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Cuisine).where(Cuisine.id == cuisine_id))
    c = result.scalar_one_or_none()
    if not c:
        raise HTTPException(404, "Cuisine not found")

    # Count restaurants linked to this cuisine
    cnt = (await db.execute(
        select(func.count(Restaurant.id)).where(Restaurant.cuisine_id == cuisine_id)
    )).scalar()

    # Get linked restaurants (first 20)
    rest_result = await db.execute(
        select(Restaurant)
        .where(Restaurant.cuisine_id == cuisine_id)
        .order_by(Restaurant.rating.desc().nulls_last())
        .limit(20)
    )
    restaurants = rest_result.scalars().all()

    return {
        **_serialize(c, cnt),
        "restaurants": [
            {"id": r.id, "name": r.name, "city": r.city, "borough": r.borough, "rating": r.rating}
            for r in restaurants
        ],
    }


@router.patch("/{cuisine_id}")
async def update_cuisine(cuisine_id: int, data: dict, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Cuisine).where(Cuisine.id == cuisine_id))
    c = result.scalar_one_or_none()
    if not c:
        raise HTTPException(404, "Cuisine not found")
    allowed = {"description", "key_ingredients", "key_techniques", "flavor_profile",
               "typical_dishes", "differentiating_factors", "sub_region"}
    for k, v in data.items():
        if k in allowed:
            setattr(c, k, v)
    await db.commit()
    await db.refresh(c)
    return _serialize(c, 0)


def _serialize(c: Cuisine, restaurant_count: int = 0) -> dict:
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
        "restaurant_count": restaurant_count,
    }
