"""Map endpoint — returns GeoJSON for the restaurant map."""
import json as _json
from collections import defaultdict
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from backend.database import get_db
from backend.models import Restaurant, Recommendation, Contact

router = APIRouter(prefix="/map", tags=["map"])


@router.get("/geojson")
async def get_geojson(
    city: str = "New York",
    cuisine_id: int = None,
    min_rating: float = None,
    min_member_rating: float = None,
    member_picks_only: bool = False,
    borough: str = None,
    neighborhood: str = None,
    price_level: int = None,
    sort_by: str = "member_rating",   # "member_rating" | "rating"
    db: AsyncSession = Depends(get_db),
):
    q = (
        select(
            Restaurant,
            func.avg(Recommendation.rating).label("member_avg"),
            func.count(Recommendation.id).label("rec_count"),
        )
        .outerjoin(Recommendation, Recommendation.restaurant_id == Restaurant.id)
        .where(Restaurant.lat.is_not(None), Restaurant.lng.is_not(None))
        .group_by(Restaurant.id)
    )
    if city:
        q = q.where(Restaurant.city.ilike(f"%{city}%"))
    if cuisine_id:
        q = q.where(Restaurant.cuisine_id == cuisine_id)
    if min_rating:
        q = q.where(Restaurant.rating >= min_rating)
    if borough:
        q = q.where(Restaurant.borough == borough)
    if neighborhood:
        q = q.where(Restaurant.neighborhood.ilike(f"%{neighborhood}%"))
    if price_level:
        q = q.where(Restaurant.price_level == price_level)
    if member_picks_only:
        q = q.having(func.count(Recommendation.id) > 0)
    if min_member_rating:
        q = q.having(func.avg(Recommendation.rating) >= min_member_rating)

    if sort_by == "rating":
        q = q.order_by(Restaurant.rating.desc().nulls_last())
    else:
        q = q.order_by(func.avg(Recommendation.rating).desc().nulls_last())

    result = await db.execute(q)
    rows = result.all()

    # Batch-load recommendation tags for all returned restaurants
    restaurant_ids = [r.id for r, _, _ in rows]
    tags_by_restaurant: dict[int, set] = defaultdict(set)
    if restaurant_ids:
        tag_q = select(Recommendation.restaurant_id, Recommendation.tags).where(
            Recommendation.restaurant_id.in_(restaurant_ids),
            Recommendation.tags.is_not(None),
        )
        tag_rows = (await db.execute(tag_q)).all()
        for rid, tag_data in tag_rows:
            try:
                tag_list = _json.loads(tag_data) if isinstance(tag_data, str) else (tag_data or [])
                for t in tag_list:
                    tags_by_restaurant[rid].add(t.lower())
            except Exception:
                pass

    features = []
    for restaurant, member_avg, rec_count in rows:
        features.append({
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [restaurant.lng, restaurant.lat],
            },
            "properties": {
                "id": restaurant.id,
                "name": restaurant.name,
                "address": restaurant.address,
                "city": restaurant.city,
                "neighborhood": restaurant.neighborhood,
                "borough": restaurant.borough,
                "cuisine": restaurant.cuisine_raw,
                "rating": restaurant.rating,
                "price_level": restaurant.price_level,
                "website": restaurant.website,
                "phone": restaurant.phone,
                "notes": restaurant.notes,
                "source": restaurant.source,
                "member_avg_rating": round(float(member_avg), 1) if member_avg else None,
                "recommendation_count": rec_count,
                "all_tags": sorted(tags_by_restaurant.get(restaurant.id, [])),
            },
        })

    return {
        "type": "FeatureCollection",
        "features": features,
        "meta": {"total": len(features)},
    }


@router.get("/restaurant/{restaurant_id}/picks")
async def get_restaurant_picks(
    restaurant_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Returns individual member recommendations for a restaurant."""
    q = (
        select(Recommendation)
        .where(Recommendation.restaurant_id == restaurant_id)
        .options(selectinload(Recommendation.contact))
        .order_by(Recommendation.rating.desc().nulls_last())
    )
    result = await db.execute(q)
    recs = result.scalars().all()
    return [
        {
            "id": r.id,
            "member_name": r.contact.name if r.contact else "Anonymous",
            "rating": r.rating,
            "notes": r.notes,
            "tags": r.tags or [],
            "visited_at": r.visited_at.isoformat() if r.visited_at else None,
        }
        for r in recs
    ]


@router.get("/neighborhoods")
async def get_neighborhoods(
    city: str = "New York",
    db: AsyncSession = Depends(get_db),
):
    """Returns distinct borough + neighborhood values for filter dropdowns."""
    borough_q = (
        select(Restaurant.borough)
        .where(Restaurant.borough.is_not(None), Restaurant.city.ilike(f"%{city}%"))
        .distinct()
        .order_by(Restaurant.borough)
    )
    hood_q = (
        select(Restaurant.neighborhood)
        .where(Restaurant.neighborhood.is_not(None), Restaurant.city.ilike(f"%{city}%"))
        .distinct()
        .order_by(Restaurant.neighborhood)
    )
    boroughs = (await db.execute(borough_q)).scalars().all()
    neighborhoods = (await db.execute(hood_q)).scalars().all()
    return {"boroughs": list(boroughs), "neighborhoods": list(neighborhoods)}


@router.get("/activity")
async def get_activity(
    limit: int = Query(30, le=100),
    db: AsyncSession = Depends(get_db),
):
    """Recent member picks — for the activity feed."""
    q = (
        select(Recommendation)
        .options(
            selectinload(Recommendation.contact),
            selectinload(Recommendation.restaurant),
        )
        .where(Recommendation.rating.is_not(None))
        .order_by(Recommendation.created_at.desc())
        .limit(limit)
    )
    result = await db.execute(q)
    recs = result.scalars().all()
    return [
        {
            "id": r.id,
            "member_name": r.contact.name if r.contact else "Anonymous",
            "restaurant_id": r.restaurant_id,
            "restaurant_name": r.restaurant.name if r.restaurant else "Unknown",
            "restaurant_cuisine": r.restaurant.cuisine_raw if r.restaurant else None,
            "restaurant_neighborhood": (r.restaurant.neighborhood or r.restaurant.borough) if r.restaurant else None,
            "rating": r.rating,
            "notes": r.notes,
            "tags": r.tags or [],
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in recs
    ]


@router.get("/stats")
async def get_stats(db: AsyncSession = Depends(get_db)):
    """Dashboard summary stats."""
    total_restaurants = (await db.execute(select(func.count(Restaurant.id)))).scalar()
    total_with_coords = (await db.execute(
        select(func.count(Restaurant.id)).where(Restaurant.lat.is_not(None))
    )).scalar()
    total_recs = (await db.execute(select(func.count(Recommendation.id)))).scalar()
    avg_rec = (await db.execute(select(func.avg(Recommendation.rating)))).scalar()

    return {
        "total_restaurants": total_restaurants,
        "mapped_restaurants": total_with_coords,
        "total_recommendations": total_recs,
        "average_member_rating": round(float(avg_rec), 2) if avg_rec else None,
    }
