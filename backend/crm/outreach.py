"""
Email outreach — renders Jinja2 templates and sends via SMTP.
Logs every send to OutreachLog.
"""
import json
import smtplib
import ssl
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from jinja2 import Environment, BaseLoader
from openai import AsyncOpenAI
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from backend.models import OutreachTemplate, OutreachLog, Contact, EventInvite, Event
from backend.config import get_settings

_jinja = Environment(loader=BaseLoader())
CHAT_MODEL = "gpt-4o-mini"


def _ai_client() -> AsyncOpenAI:
    return AsyncOpenAI(api_key=get_settings().openai_api_key)


# ─── Templates ───────────────────────────────────────────────────────────────

async def create_template(db: AsyncSession, data: dict) -> OutreachTemplate:
    tpl = OutreachTemplate(**{k: v for k, v in data.items() if hasattr(OutreachTemplate, k)})
    db.add(tpl)
    await db.commit()
    await db.refresh(tpl)
    return tpl


async def list_templates(db: AsyncSession) -> list[OutreachTemplate]:
    result = await db.execute(select(OutreachTemplate).order_by(OutreachTemplate.name))
    return result.scalars().all()


async def update_template(db: AsyncSession, template_id: int, data: dict) -> OutreachTemplate | None:
    result = await db.execute(select(OutreachTemplate).where(OutreachTemplate.id == template_id))
    tpl = result.scalar_one_or_none()
    if not tpl:
        return None
    for k, v in data.items():
        if hasattr(OutreachTemplate, k):
            setattr(tpl, k, v)
    await db.commit()
    await db.refresh(tpl)
    return tpl


async def delete_template(db: AsyncSession, template_id: int) -> bool:
    result = await db.execute(select(OutreachTemplate).where(OutreachTemplate.id == template_id))
    tpl = result.scalar_one_or_none()
    if not tpl:
        return False
    await db.delete(tpl)
    await db.commit()
    return True


async def generate_template_with_ai(
    description: str,
    type_: str = "custom",
    context: dict = None,
) -> dict:
    """
    Use GPT to draft an email template from a natural-language description.
    Returns { name, subject, body } with Jinja2 variables embedded.
    """
    context = context or {}
    available_vars = [
        "{{ name }} — recipient's name",
        "{{ event_name }} — name of the dining event",
        "{{ event_date }} — formatted date and time",
        "{{ event_location }} — venue or address",
        "{{ event_description }} — event details",
        "{{ restaurant_name }} — restaurant name",
        "{{ cuisine }} — cuisine type",
        "{{ rsvp_link }} — clickable RSVP URL (wrap in <a href='{{ rsvp_link }}'>...</a> for invite emails)",
    ]
    extra_context = "\n".join(f"- {k}: {v}" for k, v in context.items()) if context else "None provided"

    prompt = f"""You are a copywriter and HTML email designer for GAB, an exclusive dining club in NYC. GAB's aesthetic is warm, sophisticated, and slightly literary — cultured but never stuffy.

Write an HTML email template based on this brief:
"{description}"

Template type: {type_}

Available Jinja2 variables you may use:
{chr(10).join("- " + v for v in available_vars)}

Extra context from the user:
{extra_context}

VISUAL STYLE REFERENCE — GAB uses these design aesthetics (pick the one that fits the brief):
- "The Ribbon": cream (#f5f0e8) background, red (#c0392b) decorative border with corner ornaments, elegant serif typography
- "Candlelight": near-black (#111008) background, warm amber/gold (#d4aa4a) text, string-light motifs, intimate atmosphere
- "Mediterranean Table": warm white (#fffdf8), terracotta (#c0583a) accents, botanical emoji (🍋🫒🌿), checkered divider, Italian warmth
- "Red Velvet": deep crimson (#7a0e18) background, gold stars (✦), torn-paper contrast accent, glamorous and celebratory
- "The Menu Card": very dark brown (#1a1008), gold (#c8a840) script, ornate corner flourishes (❧), formal tasting-menu aesthetic
- "The Arch": blush (#fdf5f0) background, thin red arch SVG, sparkle stars (✦), playful cocktail-bar energy

Rules:
- Use Jinja2 variable syntax: {{{{ name }}}}, {{{{ event_name }}}}, etc. (double braces)
- Full inline-CSS HTML only (no <html>/<head> wrapper)
- Use a <div> wrapper with max-width:600px and appropriate background color
- All CSS must be inline (style="...") — no <style> blocks
- Subject line should be compelling and specific to the event
- Sign off as "GAB Dining Club"
- Tone: warm, specific, poetic where appropriate — never generic

Return ONLY valid JSON:
{{
  "name": "descriptive template name",
  "subject": "subject line with {{{{ variables }}}}",
  "body": "full inline-CSS HTML body"
}}"""

    client = _ai_client()
    resp = await client.chat.completions.create(
        model=CHAT_MODEL,
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
    )
    result = json.loads(resp.choices[0].message.content)
    result["type"] = type_
    return result


def render_template(template_body: str, template_subject: str, context: dict) -> tuple[str, str]:
    """Render Jinja2 subject and body with given context variables."""
    subject = _jinja.from_string(template_subject).render(**context)
    body = _jinja.from_string(template_body).render(**context)
    return subject, body


# ─── Sending ─────────────────────────────────────────────────────────────────

async def send_email(
    db: AsyncSession,
    contact_id: int,
    subject: str,
    body: str,
    template_id: int = None,
    html: bool = True,
) -> OutreachLog:
    """Send a single email to a contact and log it."""
    settings = get_settings()

    contact_result = await db.execute(select(Contact).where(Contact.id == contact_id))
    contact = contact_result.scalar_one_or_none()
    if not contact or not contact.email:
        raise ValueError(f"Contact {contact_id} has no email address")

    _send_smtp(
        to_email=contact.email,
        to_name=contact.name,
        subject=subject,
        body=body,
        html=html,
        settings=settings,
    )

    log = OutreachLog(
        contact_id=contact_id,
        template_id=template_id,
        subject=subject,
        body=body,
        sent_at=datetime.utcnow(),
        status="sent",
    )
    db.add(log)
    await db.commit()
    return log


async def send_event_invites(
    db: AsyncSession,
    event_id: int,
    template_id: int,
) -> dict:
    """
    Send invite emails to all contacts invited to an event (status='invited', not yet sent).
    Returns {"sent": N, "failed": N, "skipped": N}
    """
    event_result = await db.execute(select(Event).where(Event.id == event_id))
    event = event_result.scalar_one_or_none()
    if not event:
        raise ValueError(f"Event {event_id} not found")

    tpl_result = await db.execute(select(OutreachTemplate).where(OutreachTemplate.id == template_id))
    template = tpl_result.scalar_one_or_none()
    if not template:
        raise ValueError(f"Template {template_id} not found")

    invites_result = await db.execute(
        select(EventInvite, Contact)
        .join(Contact, EventInvite.contact_id == Contact.id)
        .where(EventInvite.event_id == event_id, EventInvite.sent_at.is_(None))
    )
    rows = invites_result.all()

    sent = failed = skipped = 0
    settings = get_settings()

    for invite, contact in rows:
        if not contact.email:
            skipped += 1
            continue
        base_url = settings.base_url.rstrip("/") if hasattr(settings, "base_url") and settings.base_url else ""
        rsvp_link = f"{base_url}/rsvp/{invite.rsvp_token}" if invite.rsvp_token else ""
        ctx = {
            "name": contact.name,
            "event_name": event.name,
            "event_date": event.date.strftime("%A, %B %d %Y at %H:%M") if event.date else "TBD",
            "event_location": event.location or "TBD",
            "event_description": event.description or "",
            "rsvp_link": rsvp_link,
        }
        subject, body = render_template(template.body, template.subject, ctx)
        try:
            _send_smtp(contact.email, contact.name, subject, body, html=True, settings=settings)
            invite.sent_at = datetime.utcnow()
            db.add(OutreachLog(
                contact_id=contact.id,
                template_id=template_id,
                subject=subject,
                body=body,
                sent_at=datetime.utcnow(),
                status="sent",
            ))
            sent += 1
        except Exception as e:
            failed += 1

    await db.commit()
    return {"sent": sent, "failed": failed, "skipped": skipped}


# ─── SMTP helper ─────────────────────────────────────────────────────────────

def _send_smtp(to_email: str, to_name: str, subject: str, body: str, html: bool, settings):
    if not settings.smtp_user or not settings.smtp_password:
        raise RuntimeError("SMTP credentials not configured in .env")

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"{settings.from_name} <{settings.from_email}>"
    msg["To"] = f"{to_name} <{to_email}>"

    part = MIMEText(body, "html" if html else "plain", "utf-8")
    msg.attach(part)

    context = ssl.create_default_context()
    with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
        server.ehlo()
        server.starttls(context=context)
        server.login(settings.smtp_user, settings.smtp_password)
        server.sendmail(settings.from_email, to_email, msg.as_string())


# ─── Default templates ────────────────────────────────────────────────────────

DEFAULT_TEMPLATES = [
    {
        "name": "Event Invite",
        "type": "invite",
        "subject": "You're invited: {{ event_name }}",
        "body": """<h2>Hi {{ name }},</h2>
<p>You're invited to <strong>{{ event_name }}</strong>.</p>
<p><strong>When:</strong> {{ event_date }}<br>
<strong>Where:</strong> {{ event_location }}</p>
<p>{{ event_description }}</p>
<p>Please reply to let us know if you can make it.</p>
<p>With love,<br>GAB Dining Club</p>""",
    },
    {
        "name": "Event Follow-up",
        "type": "followup",
        "subject": "Thanks for joining us at {{ event_name }}",
        "body": """<h2>Hi {{ name }},</h2>
<p>Thank you for joining us at <strong>{{ event_name }}</strong> — it was wonderful having you!</p>
<p>We'd love to hear your thoughts on the experience.</p>
<p>With love,<br>GAB Dining Club</p>""",
    },
    {
        "name": "Member Welcome",
        "type": "welcome",
        "subject": "Welcome to GAB Dining Club, {{ name }}!",
        "body": """<h2>Welcome, {{ name }}!</h2>
<p>We're thrilled to have you as a member of <strong>GAB Dining Club</strong>.</p>
<p>Expect invitations to exclusive dining experiences, curated by our community of food lovers.</p>
<p>With love,<br>GAB Dining Club</p>""",
    },
]


async def seed_default_templates(db: AsyncSession) -> int:
    from backend.crm.template_designs import DESIGNED_TEMPLATES
    inserted = 0
    all_templates = DEFAULT_TEMPLATES + DESIGNED_TEMPLATES
    for data in all_templates:
        existing = await db.execute(select(OutreachTemplate).where(OutreachTemplate.name == data["name"]))
        if existing.scalar_one_or_none():
            continue
        db.add(OutreachTemplate(**data))
        inserted += 1
    await db.commit()
    return inserted
