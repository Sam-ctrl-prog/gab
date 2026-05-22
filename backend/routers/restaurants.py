from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from backend.database import get_db
from backend.models import Restaurant, Cuisine
from backend.scraper.runner import run_scrape
from backend.scraper.seed_nyc import seed_nyc
from backend.scraper.seed_menus import seed_menus

router = APIRouter(prefix="/restaurants", tags=["restaurants"])


@router.get("")
async def list_restaurants(
    city: str = None,
    country: str = None,
    cuisine_id: int = None,
    search: str = None,
    neighborhood: str = None,
    borough: str = None,
    limit: int = Query(50, le=200),
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
):
    q = select(Restaurant)
    if city:
        q = q.where(Restaurant.city.ilike(f"%{city}%"))
    if country:
        q = q.where(Restaurant.country.ilike(f"%{country}%"))
    if cuisine_id:
        q = q.where(Restaurant.cuisine_id == cuisine_id)
    if search:
        term = f"%{search}%"
        q = q.where(or_(Restaurant.name.ilike(term), Restaurant.cuisine_raw.ilike(term)))
    if neighborhood:
        q = q.where(Restaurant.neighborhood.ilike(f"%{neighborhood}%"))
    if borough:
        q = q.where(Restaurant.borough == borough)
    q = q.order_by(Restaurant.rating.desc().nulls_last()).limit(limit).offset(offset)
    result = await db.execute(q)
    restaurants = result.scalars().all()
    return [_serialize(r) for r in restaurants]


@router.get("/{restaurant_id}")
async def get_restaurant(restaurant_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Restaurant).where(Restaurant.id == restaurant_id))
    r = result.scalar_one_or_none()
    if not r:
        raise HTTPException(404, "Restaurant not found")
    return _serialize(r)


@router.post("")
async def create_restaurant(data: dict, db: AsyncSession = Depends(get_db)):
    r = Restaurant(**{k: v for k, v in data.items() if hasattr(Restaurant, k)})
    db.add(r)
    await db.commit()
    await db.refresh(r)
    return _serialize(r)


@router.patch("/{restaurant_id}")
async def update_restaurant(restaurant_id: int, data: dict, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Restaurant).where(Restaurant.id == restaurant_id))
    r = result.scalar_one_or_none()
    if not r:
        raise HTTPException(404, "Restaurant not found")
    for k, v in data.items():
        if hasattr(Restaurant, k):
            setattr(r, k, v)
    await db.commit()
    await db.refresh(r)
    return _serialize(r)


@router.delete("/{restaurant_id}")
async def delete_restaurant(restaurant_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Restaurant).where(Restaurant.id == restaurant_id))
    r = result.scalar_one_or_none()
    if not r:
        raise HTTPException(404, "Restaurant not found")
    await db.delete(r)
    await db.commit()
    return {"deleted": True}


@router.post("/scrape")
async def scrape_restaurants(
    city: str,
    cuisine: str = "",
    country: str = "US",
    source: str = "openstreetmap",
    max_results: int = 60,
    db: AsyncSession = Depends(get_db),
):
    """Trigger a single scrape job and persist results."""
    summary = await run_scrape(db=db, city=city, cuisine=cuisine, country=country, source=source, max_results=max_results)
    return summary


@router.post("/seed-nyc")
async def seed_nyc_restaurants(background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db)):
    """
    Run a full NYC scrape across all 5 boroughs and 18 cuisine types.
    Runs in the background — returns immediately with a confirmation.
    Check /map/stats to monitor progress.
    """
    background_tasks.add_task(seed_nyc, db)
    return {"status": "started", "message": "Full NYC scrape running in background. Check /map/stats for progress."}


@router.post("/seed-menus")
async def seed_menus_endpoint(background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db)):
    """
    For every restaurant with a website and no menu yet, scrape and index the menu.
    Auto-runs cuisine matching after each successful ingest.
    Runs in the background.
    """
    background_tasks.add_task(seed_menus, db)
    return {"status": "started", "message": "Menu seeding running in background. Check /menus for progress."}


def _serialize(r: Restaurant) -> dict:
    return {
        "id": r.id,
        "name": r.name,
        "address": r.address,
        "city": r.city,
        "country": r.country,
        "lat": r.lat,
        "lng": r.lng,
        "cuisine_id": r.cuisine_id,
        "cuisine_raw": r.cuisine_raw,
        "rating": r.rating,
        "price_level": r.price_level,
        "phone": r.phone,
        "website": r.website,
        "menu_url": r.menu_url,
        "google_place_id": r.google_place_id,
        "neighborhood": r.neighborhood,
        "borough": r.borough,
        "source": r.source,
        "notes": r.notes,
        "photo_url": r.photo_url,
        "created_at": r.created_at.isoformat() if r.created_at else None,
    }
