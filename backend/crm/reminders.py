"""
Event reminder automation.
Runs on a schedule — finds events happening in ~24h and sends reminder emails
to all invited/accepted guests. Marks reminder_sent=True to prevent duplicates.
"""
from datetime import datetime, timedelta, timezone
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy import select
from backend.models import Event, EventInvite, Contact, OutreachTemplate
from backend.crm.outreach import render_template, _send_smtp
from backend.config import get_settings
from rich.console import Console

console = Console()

REMINDER_WINDOW_MIN = 18   # hours before event — start of send window
REMINDER_WINDOW_MAX = 30   # hours before event — end of send window


async def send_reminders(db: AsyncSession) -> dict:
    """
    Find all events in the 18–30h window that haven't had a reminder sent,
    and email all guests (invited or accepted).
    Returns {"events_processed": N, "emails_sent": N, "errors": N}
    """
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    window_start = now + timedelta(hours=REMINDER_WINDOW_MIN)
    window_end   = now + timedelta(hours=REMINDER_WINDOW_MAX)

    # Find qualifying events
    result = await db.execute(
        select(Event).where(
            Event.date >= window_start,
            Event.date <= window_end,
            Event.reminder_sent == False,
            Event.status.in_(["confirmed", "draft"]),
        )
    )
    events = result.scalars().all()

    if not events:
        console.print("[dim]Reminders: no events in window[/]")
        return {"events_processed": 0, "emails_sent": 0, "errors": 0}

    # Load reminder template (or use built-in fallback)
    tpl_result = await db.execute(
        select(OutreachTemplate).where(OutreachTemplate.type == "reminder")
    )
    tpl = tpl_result.scalars().first()

    settings = get_settings()
    emails_sent = errors = 0

    for event in events:
        console.print(f"[cyan]Sending reminders for:[/] {event.name} on {event.date}")

        # Get all invited/accepted guests
        guests_result = await db.execute(
            select(EventInvite, Contact)
            .join(Contact, EventInvite.contact_id == Contact.id)
            .where(
                EventInvite.event_id == event.id,
                EventInvite.status.in_(["invited", "accepted"]),
            )
        )
        guests = guests_result.all()

        for invite, contact in guests:
            if not contact.email:
                continue

            base_url = settings.base_url.rstrip("/") if hasattr(settings, "base_url") and settings.base_url else ""
            rsvp_link = f"{base_url}/rsvp/{invite.rsvp_token}" if invite.rsvp_token else ""
            ctx = {
                "name": contact.name,
                "event_name": event.name,
                "event_date": event.date.strftime("%A, %B %d at %I:%M %p") if event.date else "TBD",
                "event_location": event.location or "TBD",
                "event_description": event.description or "",
                "rsvp_link": rsvp_link,
            }

            if tpl:
                subject, body = render_template(tpl.body, tpl.subject, ctx)
            else:
                subject, body = _default_reminder(ctx)

            try:
                _send_smtp(
                    to_email=contact.email,
                    to_name=contact.name,
                    subject=subject,
                    body=body,
                    html=True,
                    settings=settings,
                )
                emails_sent += 1
                console.print(f"  [green]✓[/] {contact.name} <{contact.email}>")
            except Exception as e:
                errors += 1
                console.print(f"  [red]✗[/] {contact.name}: {e}")

        event.reminder_sent = True

    await db.commit()

    summary = {"events_processed": len(events), "emails_sent": emails_sent, "errors": errors}
    console.print(f"[green]Reminders done:[/] {summary}")
    return summary


def _default_reminder(ctx: dict) -> tuple[str, str]:
    """Built-in reminder template used when no 'reminder' type template exists in DB."""
    subject = f"Reminder: {ctx['event_name']} is tomorrow"
    body = f"""<div style="background:#111008;padding:40px 48px;font-family:Georgia,serif;max-width:560px;margin:0 auto;">
  <p style="margin:0 0 4px;font-size:10px;letter-spacing:0.22em;text-transform:uppercase;color:#5a4e38;">GAB DINING CLUB · REMINDER</p>
  <h2 style="margin:12px 0 8px;font-size:26px;font-weight:normal;color:#d4aa4a;">{ctx['event_name']}</h2>
  <div style="width:40px;height:1px;background:#3a3020;margin:16px 0;"></div>
  <p style="font-size:16px;color:#c8b870;font-style:italic;margin:0 0 20px;">Dear {ctx['name']},</p>
  <p style="font-size:14px;color:#a09070;line-height:1.85;margin:0 0 24px;">
    Just a reminder that <strong style="color:#d4aa4a;">{ctx['event_name']}</strong> is coming up.
  </p>
  <div style="border:1px solid #2e2818;padding:18px 22px;margin-bottom:24px;">
    <p style="margin:0 0 6px;font-size:10px;letter-spacing:0.14em;text-transform:uppercase;color:#5a4e38;">When</p>
    <p style="margin:0 0 14px;font-size:15px;color:#c8b870;font-style:italic;">{ctx['event_date']}</p>
    <p style="margin:0 0 6px;font-size:10px;letter-spacing:0.14em;text-transform:uppercase;color:#5a4e38;">Where</p>
    <p style="margin:0;font-size:15px;color:#c8b870;font-style:italic;">{ctx['event_location']}</p>
  </div>
  <p style="font-size:13px;color:#5a4e38;margin:0 0 24px;">We look forward to seeing you at the table.</p>
  <p style="font-size:11px;font-style:italic;color:#3a3020;letter-spacing:0.08em;">WITH LOVE · GAB DINING CLUB</p>
</div>"""
    return subject, body


# ── Seed reminder template ────────────────────────────────────────────────────

REMINDER_TEMPLATE = {
    "name": "Event Reminder",
    "type": "reminder",
    "subject": "Reminder: {{ event_name }} is tomorrow",
    "body": """<div style="background:#111008;padding:40px 48px;font-family:Georgia,serif;max-width:560px;margin:0 auto;">
  <p style="margin:0 0 4px;font-size:10px;letter-spacing:0.22em;text-transform:uppercase;color:#5a4e38;">GAB DINING CLUB · REMINDER</p>
  <h2 style="margin:12px 0 8px;font-size:26px;font-weight:normal;color:#d4aa4a;">{{ event_name }}</h2>
  <div style="width:40px;height:1px;background:#3a3020;margin:16px 0;"></div>
  <p style="font-size:16px;color:#c8b870;font-style:italic;margin:0 0 20px;">Dear {{ name }},</p>
  <p style="font-size:14px;color:#a09070;line-height:1.85;margin:0 0 24px;">
    Just a friendly reminder that <strong style="color:#d4aa4a;">{{ event_name }}</strong> is coming up tomorrow.
  </p>
  <div style="border:1px solid #2e2818;padding:18px 22px;margin-bottom:24px;">
    <p style="margin:0 0 6px;font-size:10px;letter-spacing:0.14em;text-transform:uppercase;color:#5a4e38;">When</p>
    <p style="margin:0 0 14px;font-size:15px;color:#c8b870;font-style:italic;">{{ event_date }}</p>
    <p style="margin:0 0 6px;font-size:10px;letter-spacing:0.14em;text-transform:uppercase;color:#5a4e38;">Where</p>
    <p style="margin:0;font-size:15px;color:#c8b870;font-style:italic;">{{ event_location }}</p>
  </div>
  <p style="font-size:13px;color:#5a4e38;margin:0 0 24px;">We look forward to seeing you at the table tomorrow.</p>
  <p style="font-size:11px;font-style:italic;color:#3a3020;letter-spacing:0.08em;">WITH LOVE · GAB DINING CLUB</p>
</div>""",
}
