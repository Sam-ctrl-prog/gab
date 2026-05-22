"""Event and invite management for dining club gatherings."""
import secrets
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from backend.models import Event, EventInvite, Contact


def _make_token() -> str:
    return secrets.token_urlsafe(32)


async def create_event(db: AsyncSession, data: dict) -> Event:
    event = Event(**{k: v for k, v in data.items() if hasattr(Event, k)})
    db.add(event)
    await db.commit()
    await db.refresh(event)
    return event


async def get_event(db: AsyncSession, event_id: int) -> Event | None:
    result = await db.execute(select(Event).where(Event.id == event_id))
    return result.scalar_one_or_none()


async def list_events(db: AsyncSession, status: str = None) -> list[Event]:
    q = select(Event).order_by(Event.date.desc())
    if status:
        q = q.where(Event.status == status)
    result = await db.execute(q)
    return result.scalars().all()


async def update_event(db: AsyncSession, event_id: int, data: dict) -> Event | None:
    event = await get_event(db, event_id)
    if not event:
        return None
    for k, v in data.items():
        if hasattr(Event, k):
            setattr(event, k, v)
    await db.commit()
    await db.refresh(event)
    return event


async def invite_contacts(
    db: AsyncSession,
    event_id: int,
    contact_ids: list[int],
) -> list[EventInvite]:
    """Create invite records for a list of contacts (skips duplicates)."""
    existing_result = await db.execute(
        select(EventInvite.contact_id).where(EventInvite.event_id == event_id)
    )
    already_invited = {row[0] for row in existing_result.all()}

    invites = []
    for cid in contact_ids:
        if cid in already_invited:
            continue
        invite = EventInvite(
            event_id=event_id,
            contact_id=cid,
            status="invited",
            rsvp_token=_make_token(),
        )
        db.add(invite)
        invites.append(invite)

    await db.commit()
    return invites


async def update_invite_status(
    db: AsyncSession, event_id: int, contact_id: int, status: str
) -> EventInvite | None:
    result = await db.execute(
        select(EventInvite)
        .where(EventInvite.event_id == event_id, EventInvite.contact_id == contact_id)
    )
    invite = result.scalar_one_or_none()
    if not invite:
        return None
    invite.status = status
    invite.responded_at = datetime.utcnow()
    await db.commit()
    await db.refresh(invite)
    return invite


async def get_invite_by_token(db: AsyncSession, token: str) -> tuple[EventInvite, Event, Contact] | None:
    result = await db.execute(
        select(EventInvite, Event, Contact)
        .join(Event, EventInvite.event_id == Event.id)
        .join(Contact, EventInvite.contact_id == Contact.id)
        .where(EventInvite.rsvp_token == token)
    )
    row = result.one_or_none()
    return row  # (invite, event, contact) or None


async def get_event_guest_list(db: AsyncSession, event_id: int) -> list[dict]:
    result = await db.execute(
        select(EventInvite, Contact)
        .join(Contact, EventInvite.contact_id == Contact.id)
        .where(EventInvite.event_id == event_id)
        .order_by(Contact.name)
    )
    return [
        {
            "invite_id": invite.id,
            "contact_id": contact.id,
            "name": contact.name,
            "email": contact.email,
            "phone": contact.phone,
            "status": invite.status,
            "rsvp_token": invite.rsvp_token,
            "sent_at": invite.sent_at,
            "responded_at": invite.responded_at,
            "notes": invite.notes,
        }
        for invite, contact in result.all()
    ]
