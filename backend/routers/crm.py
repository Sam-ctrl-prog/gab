from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from backend.database import get_db
from backend.models import Contact, Event, Recommendation, OutreachTemplate, OutreachLog
from backend.crm.contacts import (
    create_contact, get_contact, list_contacts, update_contact, delete_contact
)
from backend.crm.events import (
    create_event, get_event, list_events, update_event,
    invite_contacts, update_invite_status, get_event_guest_list,
)
from backend.crm.outreach import (
    create_template, list_templates, send_email, send_event_invites,
    seed_default_templates, generate_template_with_ai, update_template, delete_template,
    render_template,
)
from sqlalchemy import select
from datetime import datetime
from backend.config import get_settings

router = APIRouter(prefix="/crm", tags=["crm"])


# ─── Contacts ────────────────────────────────────────────────────────────────

@router.get("/contacts")
async def get_contacts(
    type: str = None,
    search: str = None,
    active_only: bool = True,
    db: AsyncSession = Depends(get_db),
):
    contacts = await list_contacts(db, type_filter=type, active_only=active_only, search=search)
    return [_contact_dict(c) for c in contacts]


@router.post("/contacts")
async def add_contact(data: dict, db: AsyncSession = Depends(get_db)):
    c = await create_contact(db, data)
    return _contact_dict(c)


@router.get("/contacts/{contact_id}")
async def get_contact_detail(contact_id: int, db: AsyncSession = Depends(get_db)):
    c = await get_contact(db, contact_id)
    if not c:
        raise HTTPException(404, "Contact not found")
    return _contact_dict(c)


@router.patch("/contacts/{contact_id}")
async def patch_contact(contact_id: int, data: dict, db: AsyncSession = Depends(get_db)):
    c = await update_contact(db, contact_id, data)
    if not c:
        raise HTTPException(404, "Contact not found")
    return _contact_dict(c)


@router.delete("/contacts/{contact_id}")
async def remove_contact(contact_id: int, db: AsyncSession = Depends(get_db)):
    ok = await delete_contact(db, contact_id)
    if not ok:
        raise HTTPException(404, "Contact not found")
    return {"deleted": True}


# ─── Events ──────────────────────────────────────────────────────────────────

@router.get("/events")
async def get_events(status: str = None, db: AsyncSession = Depends(get_db)):
    events = await list_events(db, status=status)
    return [_event_dict(e) for e in events]


@router.post("/events")
async def add_event(data: dict, db: AsyncSession = Depends(get_db)):
    # Accept scheduled_at as alias for date (frontend compat)
    if "scheduled_at" in data and "date" not in data:
        data["date"] = data.pop("scheduled_at")
    else:
        data.pop("scheduled_at", None)
    if "date" in data and isinstance(data["date"], str):
        data["date"] = datetime.fromisoformat(data["date"])
    e = await create_event(db, data)
    return _event_dict(e)


@router.get("/events/{event_id}")
async def get_event_detail(event_id: int, db: AsyncSession = Depends(get_db)):
    e = await get_event(db, event_id)
    if not e:
        raise HTTPException(404, "Event not found")
    return _event_dict(e)


@router.patch("/events/{event_id}")
async def patch_event(event_id: int, data: dict, db: AsyncSession = Depends(get_db)):
    if "date" in data and isinstance(data["date"], str):
        data["date"] = datetime.fromisoformat(data["date"])
    e = await update_event(db, event_id, data)
    if not e:
        raise HTTPException(404, "Event not found")
    return _event_dict(e)


@router.post("/events/{event_id}/invite")
async def invite_to_event(event_id: int, contact_ids: list[int], db: AsyncSession = Depends(get_db)):
    invites = await invite_contacts(db, event_id, contact_ids)
    return {"invited": len(invites)}


@router.get("/events/{event_id}/guests")
async def event_guests(event_id: int, db: AsyncSession = Depends(get_db)):
    return await get_event_guest_list(db, event_id)


@router.patch("/events/{event_id}/guests/{contact_id}")
async def update_guest_status(
    event_id: int, contact_id: int, status: str, db: AsyncSession = Depends(get_db)
):
    invite = await update_invite_status(db, event_id, contact_id, status)
    if not invite:
        raise HTTPException(404, "Invite not found")
    return {"status": invite.status}


@router.post("/events/{event_id}/send-invites")
async def send_invites(event_id: int, template_id: int, db: AsyncSession = Depends(get_db)):
    return await send_event_invites(db, event_id, template_id)


@router.get("/events/{event_id}/preview-email")
async def preview_event_email(event_id: int, template_id: int, db: AsyncSession = Depends(get_db)):
    """Render a template with real event data for preview. Uses first guest as sample contact."""
    from backend.models import EventInvite
    event = await get_event(db, event_id)
    if not event:
        raise HTTPException(404, "Event not found")
    tpl_result = await db.execute(select(OutreachTemplate).where(OutreachTemplate.id == template_id))
    tpl = tpl_result.scalar_one_or_none()
    if not tpl:
        raise HTTPException(404, "Template not found")

    # Use first invited contact as sample, fall back to placeholder
    sample_result = await db.execute(
        select(Contact)
        .join(EventInvite, EventInvite.contact_id == Contact.id)
        .where(EventInvite.event_id == event_id)
        .limit(1)
    )
    sample_contact = sample_result.scalar_one_or_none()
    name = sample_contact.name if sample_contact else "Jane Smith"

    settings = get_settings()
    base_url = settings.base_url.rstrip("/")
    ctx = {
        "name": name,
        "event_name": event.name,
        "event_date": event.date.strftime("%A, %B %d %Y at %I:%M %p") if event.date else "TBD",
        "event_location": event.location or "TBD",
        "event_description": event.description or "",
        "rsvp_link": f"{base_url}/rsvp/EXAMPLE_TOKEN",
        "restaurant_name": "",
        "cuisine": "",
    }
    subject, body = render_template(tpl.body, tpl.subject, ctx)
    return {"subject": subject, "body": body}


# ─── Outreach templates ───────────────────────────────────────────────────────

@router.get("/templates")
async def get_templates(db: AsyncSession = Depends(get_db)):
    tpls = await list_templates(db)
    return [{"id": t.id, "name": t.name, "type": t.type, "subject": t.subject, "body": t.body} for t in tpls]


@router.get("/templates/{template_id}")
async def get_template(template_id: int, db: AsyncSession = Depends(get_db)):
    from sqlalchemy import select
    result = await db.execute(select(OutreachTemplate).where(OutreachTemplate.id == template_id))
    t = result.scalar_one_or_none()
    if not t:
        raise HTTPException(404, "Template not found")
    return {"id": t.id, "name": t.name, "type": t.type, "subject": t.subject, "body": t.body}


@router.post("/templates")
async def add_template(data: dict, db: AsyncSession = Depends(get_db)):
    t = await create_template(db, data)
    return {"id": t.id, "name": t.name, "type": t.type, "subject": t.subject, "body": t.body}


@router.patch("/templates/{template_id}")
async def patch_template(template_id: int, data: dict, db: AsyncSession = Depends(get_db)):
    t = await update_template(db, template_id, data)
    if not t:
        raise HTTPException(404, "Template not found")
    return {"id": t.id, "name": t.name, "type": t.type, "subject": t.subject, "body": t.body}


@router.delete("/templates/{template_id}")
async def remove_template(template_id: int, db: AsyncSession = Depends(get_db)):
    ok = await delete_template(db, template_id)
    if not ok:
        raise HTTPException(404, "Template not found")
    return {"deleted": True}


@router.post("/templates/seed")
async def seed_templates(db: AsyncSession = Depends(get_db)):
    count = await seed_default_templates(db)
    return {"inserted": count}


@router.post("/templates/generate")
async def ai_generate_template(data: dict):
    """
    Generate a template with AI.
    Body: { "description": "...", "type": "invite|followup|welcome|custom", "context": {...} }
    Returns: { "name": "...", "subject": "...", "body": "..." }
    """
    description = data.get("description", "")
    type_ = data.get("type", "custom")
    context = data.get("context", {})
    if not description:
        raise HTTPException(400, "description is required")
    return await generate_template_with_ai(description, type_, context)


@router.post("/send")
async def send(
    contact_id: int,
    subject: str,
    body: str,
    template_id: int = None,
    db: AsyncSession = Depends(get_db),
):
    log = await send_email(db, contact_id, subject, body, template_id)
    return {"log_id": log.id, "status": log.status}


@router.post("/templates/{template_id}/render")
async def render_template_for_contact(
    template_id: int,
    contact_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Render a template with a contact's data — returns subject + body preview."""
    tpl_result = await db.execute(select(OutreachTemplate).where(OutreachTemplate.id == template_id))
    tpl = tpl_result.scalar_one_or_none()
    if not tpl:
        raise HTTPException(404, "Template not found")
    contact_result = await db.execute(select(Contact).where(Contact.id == contact_id))
    contact = contact_result.scalar_one_or_none()
    if not contact:
        raise HTTPException(404, "Contact not found")
    ctx = {"name": contact.name, "event_name": "", "event_date": "", "event_location": "", "event_description": "", "rsvp_link": ""}
    subject, body = render_template(tpl.body, tpl.subject, ctx)
    return {"subject": subject, "body": body}


@router.get("/outreach-log")
async def get_outreach_log(
    contact_id: int = None,
    limit: int = Query(50, le=200),
    db: AsyncSession = Depends(get_db),
):
    q = (
        select(OutreachLog, Contact.name.label("contact_name"))
        .join(Contact, OutreachLog.contact_id == Contact.id)
        .order_by(OutreachLog.sent_at.desc())
        .limit(limit)
    )
    if contact_id:
        q = q.where(OutreachLog.contact_id == contact_id)
    result = await db.execute(q)
    rows = result.all()
    return [
        {
            "id": row.OutreachLog.id,
            "contact_id": row.OutreachLog.contact_id,
            "contact_name": row.contact_name,
            "subject": row.OutreachLog.subject,
            "template_id": row.OutreachLog.template_id,
            "status": row.OutreachLog.status,
            "sent_at": row.OutreachLog.sent_at.isoformat() if row.OutreachLog.sent_at else None,
        }
        for row in rows
    ]


# ─── Recommendations ─────────────────────────────────────────────────────────

@router.post("/recommendations")
async def add_recommendation(data: dict, db: AsyncSession = Depends(get_db)):
    if "visited_at" in data and isinstance(data["visited_at"], str):
        data["visited_at"] = datetime.fromisoformat(data["visited_at"])
    rec = Recommendation(**{k: v for k, v in data.items() if hasattr(Recommendation, k)})
    db.add(rec)
    await db.commit()
    await db.refresh(rec)
    return {"id": rec.id, "restaurant_id": rec.restaurant_id, "rating": rec.rating}


@router.get("/recommendations")
async def list_recommendations(restaurant_id: int = None, db: AsyncSession = Depends(get_db)):
    q = select(Recommendation).order_by(Recommendation.created_at.desc())
    if restaurant_id:
        q = q.where(Recommendation.restaurant_id == restaurant_id)
    result = await db.execute(q)
    recs = result.scalars().all()
    return [
        {
            "id": r.id,
            "restaurant_id": r.restaurant_id,
            "contact_id": r.contact_id,
            "rating": r.rating,
            "notes": r.notes,
            "tags": r.tags,
            "visited_at": r.visited_at.isoformat() if r.visited_at else None,
        }
        for r in recs
    ]


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _contact_dict(c: Contact) -> dict:
    return {
        "id": c.id, "name": c.name, "type": c.type, "email": c.email,
        "phone": c.phone, "restaurant_id": c.restaurant_id,
        "tags": c.tags, "notes": c.notes, "active": c.active,
        "created_at": c.created_at.isoformat() if c.created_at else None,
    }


def _event_dict(e: Event) -> dict:
    iso_date = e.date.isoformat() if e.date else None
    return {
        "id": e.id, "name": e.name,
        "date": iso_date,
        "scheduled_at": iso_date,   # alias used by frontend
        "location": e.location, "restaurant_id": e.restaurant_id,
        "description": e.description, "max_guests": e.max_guests,
        "status": e.status,
        "reminder_sent": e.reminder_sent,
        "created_at": e.created_at.isoformat() if e.created_at else None,
    }
