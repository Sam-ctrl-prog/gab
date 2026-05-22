from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from backend.database import get_db
from backend.models import Menu, MenuItem, Restaurant
from backend.knowledge.menu_kb import ingest_from_url, ingest_from_text, search_menus
from backend.knowledge.cuisine_kb import match_menu_to_cuisine, match_all_unmatched

router = APIRouter(prefix="/menus", tags=["menus"])


@router.get("")
async def list_menus(restaurant_id: int = None, db: AsyncSession = Depends(get_db)):
    q = (
        select(Menu, Restaurant.name.label("restaurant_name"),
               func.count(MenuItem.id).label("item_count"))
        .join(Restaurant, Menu.restaurant_id == Restaurant.id, isouter=True)
        .outerjoin(MenuItem, MenuItem.menu_id == Menu.id)
        .group_by(Menu.id)
        .order_by(Menu.ingested_at.desc())
    )
    if restaurant_id:
        q = q.where(Menu.restaurant_id == restaurant_id)
    result = await db.execute(q)
    rows = result.all()
    return [
        {
            "id": row.Menu.id,
            "restaurant_id": row.Menu.restaurant_id,
            "restaurant_name": row.restaurant_name,
            "source_type": row.Menu.source_type,
            "source_url": row.Menu.source_url,
            "item_count": row.item_count,
            "ingested_at": row.Menu.ingested_at.isoformat() if row.Menu.ingested_at else None,
        }
        for row in rows
    ]


@router.post("/ingest/url")
async def ingest_menu_url(restaurant_id: int, url: str, db: AsyncSession = Depends(get_db)):
    menu = await ingest_from_url(db, restaurant_id, url)
    return {"menu_id": menu.id, "items_count": len(menu.items)}


@router.post("/ingest/text")
async def ingest_menu_text(restaurant_id: int, text: str, db: AsyncSession = Depends(get_db)):
    menu = await ingest_from_text(db, restaurant_id, text)
    return {"menu_id": menu.id, "items_count": len(menu.items)}


@router.get("/search")
async def search(query: str, top_k: int = 10, db: AsyncSession = Depends(get_db)):
    return await search_menus(db, query, top_k)


@router.post("/{menu_id}/match-cuisine")
async def match_cuisine(menu_id: int, db: AsyncSession = Depends(get_db)):
    """Run AI cuisine matching on a single menu."""
    result = await match_menu_to_cuisine(db, menu_id)
    return result


@router.post("/match-all")
async def match_all(background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db)):
    """Batch-match all unanalyzed menus in the background."""
    background_tasks.add_task(match_all_unmatched, db)
    return {"status": "started", "message": "Batch cuisine matching running in background."}


@router.get("/{menu_id}")
async def get_menu(menu_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Menu).where(Menu.id == menu_id))
    menu = result.scalar_one_or_none()
    if not menu:
        raise HTTPException(404, "Menu not found")
    items_result = await db.execute(select(MenuItem).where(MenuItem.menu_id == menu_id))
    items = items_result.scalars().all()
    return {
        "id": menu.id,
        "restaurant_id": menu.restaurant_id,
        "source_url": menu.source_url,
        "source_type": menu.source_type,
        "cuisine_match": menu.cuisine_match,
        "ingested_at": menu.ingested_at.isoformat() if menu.ingested_at else None,
        "items": [
            {
                "id": i.id,
                "name": i.name,
                "description": i.description,
                "price": i.price,
                "category": i.category,
            }
            for i in items
        ],
    }


@router.delete("/{menu_id}")
async def delete_menu(menu_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Menu).where(Menu.id == menu_id))
    menu = result.scalar_one_or_none()
    if not menu:
        raise HTTPException(404, "Menu not found")
    await db.delete(menu)
    await db.commit()
    return {"deleted": True}


@router.get("/restaurant/{restaurant_id}")
async def list_restaurant_menus(restaurant_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Menu).where(Menu.restaurant_id == restaurant_id))
    menus = result.scalars().all()
    return [{"id": m.id, "source_type": m.source_type, "source_url": m.source_url,
             "cuisine_match": m.cuisine_match, "ingested_at": m.ingested_at.isoformat() if m.ingested_at else None}
            for m in menus]
