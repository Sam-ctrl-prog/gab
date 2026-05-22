"""Contact management — members, restaurant POCs, vendors."""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from backend.models import Contact


async def create_contact(db: AsyncSession, data: dict) -> Contact:
    contact = Contact(**{k: v for k, v in data.items() if hasattr(Contact, k)})
    db.add(contact)
    await db.commit()
    await db.refresh(contact)
    return contact


async def get_contact(db: AsyncSession, contact_id: int) -> Contact | None:
    result = await db.execute(select(Contact).where(Contact.id == contact_id))
    return result.scalar_one_or_none()


async def list_contacts(
    db: AsyncSession,
    type_filter: str = None,
    active_only: bool = True,
    search: str = None,
) -> list[Contact]:
    q = select(Contact)
    if type_filter:
        q = q.where(Contact.type == type_filter)
    if active_only:
        q = q.where(Contact.active == True)
    if search:
        term = f"%{search}%"
        q = q.where(or_(Contact.name.ilike(term), Contact.email.ilike(term)))
    result = await db.execute(q.order_by(Contact.name))
    return result.scalars().all()


async def update_contact(db: AsyncSession, contact_id: int, data: dict) -> Contact | None:
    contact = await get_contact(db, contact_id)
    if not contact:
        return None
    for k, v in data.items():
        if hasattr(Contact, k):
            setattr(contact, k, v)
    await db.commit()
    await db.refresh(contact)
    return contact


async def delete_contact(db: AsyncSession, contact_id: int) -> bool:
    contact = await get_contact(db, contact_id)
    if not contact:
        return False
    contact.active = False  # soft delete
    await db.commit()
    return True
