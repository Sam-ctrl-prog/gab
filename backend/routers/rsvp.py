"""
Public RSVP endpoints — no auth required, token-based.
GET  /rsvp/{token}          → HTML page with Accept / Decline
POST /rsvp/{token}/respond  → updates status, returns confirmation HTML
"""
from datetime import datetime
from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from backend.database import get_db
from backend.models import EventInvite, Restaurant
from backend.crm.events import get_invite_by_token

router = APIRouter(prefix="/rsvp", tags=["rsvp"])


@router.get("/{token}", response_class=HTMLResponse)
async def rsvp_page(token: str, db: AsyncSession = Depends(get_db)):
    row = await get_invite_by_token(db, token)
    if not row:
        return _error_page("Invalid Link", "This RSVP link is invalid or has expired.")

    invite, event, contact = row

    # Accepted count + total for "X going"
    counts_result = await db.execute(
        select(
            func.count().filter(EventInvite.status.in_(["accepted", "attended"])).label("going"),
            func.count().label("total"),
        ).where(EventInvite.event_id == event.id)
    )
    counts = counts_result.one()
    going_count = counts.going or 0

    # Restaurant neighborhood/borough for "Where" row
    location_str = event.location or "TBD"
    if event.restaurant_id:
        rest_result = await db.execute(select(Restaurant).where(Restaurant.id == event.restaurant_id))
        rest = rest_result.scalar_one_or_none()
        if rest:
            parts = []
            if rest.neighborhood:
                parts.append(rest.neighborhood)
            if rest.borough:
                borough_short = {
                    "Brooklyn": "BK", "Queens": "QNS", "Bronx": "BX",
                    "Staten Island": "SI", "Manhattan": "Manhattan",
                }.get(rest.borough, rest.borough)
                parts.append(borough_short)
            if parts:
                location_str = f"{event.location or rest.name}, {', '.join(parts)}"
            elif event.location:
                location_str = event.location

    date_str = event.date.strftime("%A, %B %-d at %-I:%M %p") if event.date else "Date TBD"
    # Windows-safe strftime fallback
    try:
        date_str = event.date.strftime("%A, %B %-d at %-I:%M %p") if event.date else "Date TBD"
    except ValueError:
        date_str = event.date.strftime("%A, %B %d at %I:%M %p").replace(" 0", " ") if event.date else "Date TBD"

    already_responded = invite.status in ("accepted", "declined")

    return _page(
        contact_name=contact.name,
        event_name=event.name,
        date_str=date_str,
        location_str=location_str,
        going_count=going_count,
        token=token,
        current_status=invite.status,
        already_responded=already_responded,
        event_date_iso=event.date.isoformat() if event.date else "",
    )


@router.post("/{token}/respond", response_class=HTMLResponse)
async def rsvp_respond(token: str, action: str, db: AsyncSession = Depends(get_db)):
    """action must be 'accept' or 'decline'"""
    if action not in ("accept", "decline"):
        return HTMLResponse("<p>Invalid action.</p>", status_code=400)

    row = await get_invite_by_token(db, token)
    if not row:
        return HTMLResponse("<p>Invalid RSVP link.</p>", status_code=404)

    invite, event, contact = row
    invite.status = "accepted" if action == "accept" else "declined"
    invite.responded_at = datetime.utcnow()
    await db.commit()

    date_str = event.date.strftime("%A, %B %d at %I:%M %p") if event.date else "Date TBD"

    if action == "accept":
        headline = "See you there!"
        body = f"""
            <p style="color:#a09070;">We've noted your RSVP, {contact.name}.</p>
            <div style="border:1px solid #2e2818;padding:16px 20px;margin:20px 0;">
              <p style="margin:0 0 6px;font-size:10px;letter-spacing:.14em;text-transform:uppercase;color:#5a4e38;">Event</p>
              <p style="margin:0 0 14px;font-size:16px;color:#d4aa4a;">{event.name}</p>
              <p style="margin:0 0 6px;font-size:10px;letter-spacing:.14em;text-transform:uppercase;color:#5a4e38;">When</p>
              <p style="margin:0 0 14px;font-size:14px;color:#c8b870;">{date_str}</p>
              <p style="margin:0 0 6px;font-size:10px;letter-spacing:.14em;text-transform:uppercase;color:#5a4e38;">Where</p>
              <p style="margin:0;font-size:14px;color:#c8b870;">{event.location or 'TBD'}</p>
            </div>
            <p style="color:#5a4e38;font-size:13px;">We look forward to seeing you at the table.</p>
        """
    else:
        headline = "We'll miss you"
        body = f"""
            <p style="color:#a09070;">Thank you for letting us know, {contact.name}.</p>
            <p style="color:#5a4e38;font-size:13px;margin-top:16px;">We hope to have you at the next one.</p>
        """

    return _confirmation_page(headline, body)


# ── HTML helpers ──────────────────────────────────────────────────────────────

def _error_page(title: str, message: str) -> HTMLResponse:
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta name="color-scheme" content="light">
  <title>{title} — GAB Dining Club</title>
  <style>*{{box-sizing:border-box;margin:0;padding:0}}</style>
</head>
<body style="background:#F9F8F6;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;min-height:100vh;display:flex;align-items:center;justify-content:center;padding:24px;">
  <div style="max-width:420px;width:100%;text-align:center;">
    <div style="width:56px;height:56px;border-radius:50%;background:#F3F4F6;display:flex;align-items:center;justify-content:center;margin:0 auto 20px;">
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#9CA3AF" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>
    </div>
    <p style="font-size:11px;letter-spacing:.14em;text-transform:uppercase;color:#9CA3AF;margin-bottom:10px;">GAB Dining Club</p>
    <h1 style="font-size:22px;font-weight:600;color:#111827;margin-bottom:10px;">{title}</h1>
    <p style="font-size:15px;color:#6B7280;">{message}</p>
  </div>
</body>
</html>"""
    return HTMLResponse(html)


def _page(
    contact_name: str,
    event_name: str,
    date_str: str,
    location_str: str,
    going_count: int,
    token: str,
    current_status: str,
    already_responded: bool,
    event_date_iso: str,
) -> HTMLResponse:

    going_text = f"{going_count} going" if going_count else "Be the first to RSVP"

    if already_responded:
        status_note = f'<div style="margin-bottom:20px;padding:10px 14px;background:#F3F4F6;border-radius:8px;font-size:13px;color:#6B7280;text-align:center;">You previously <strong style="color:#111827">{"accepted" if current_status == "accepted" else "declined"}</strong> this invitation. You can change your response below.</div>'
    else:
        status_note = ""

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0">
  <meta name="color-scheme" content="light">
  <title>{event_name} — GAB Dining Club</title>
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; -webkit-text-size-adjust: 100%; }}
    body {{ background: #F9F8F6; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; min-height: 100vh; display: flex; align-items: flex-start; justify-content: center; padding: 40px 20px 60px; }}
    .card {{ max-width: 420px; width: 100%; background: #fff; border-radius: 16px; box-shadow: 0 1px 3px rgba(0,0,0,.06), 0 8px 24px rgba(0,0,0,.06); padding: 32px 28px; }}
    .icon-circle {{ width: 56px; height: 56px; border-radius: 50%; background: #EEEDFE; display: flex; align-items: center; justify-content: center; margin: 0 auto 20px; }}
    .club-label {{ font-size: 11px; letter-spacing: .14em; text-transform: uppercase; color: #9CA3AF; text-align: center; margin-bottom: 8px; }}
    .headline {{ font-size: 22px; font-weight: 700; color: #111827; text-align: center; margin-bottom: 6px; }}
    .subline {{ font-size: 14px; color: #6B7280; text-align: center; margin-bottom: 24px; }}
    .details-card {{ border: 1px solid #E5E7EB; border-radius: 12px; overflow: hidden; margin-bottom: 24px; }}
    .detail-row {{ display: flex; align-items: flex-start; gap: 12px; padding: 13px 16px; border-bottom: 0.5px solid #E5E7EB; }}
    .detail-row:last-child {{ border-bottom: none; }}
    .detail-icon {{ width: 28px; height: 28px; border-radius: 7px; background: #F9F8F6; display: flex; align-items: center; justify-content: center; flex-shrink: 0; margin-top: 1px; }}
    .detail-label {{ font-size: 10px; letter-spacing: .1em; text-transform: uppercase; color: #9CA3AF; margin-bottom: 2px; }}
    .detail-value {{ font-size: 14px; color: #111827; font-weight: 500; line-height: 1.4; }}
    .btn-accept {{ display: block; width: 100%; padding: 14px; background: #1D9E75; color: #fff; border: none; border-radius: 10px; font-size: 15px; font-weight: 600; cursor: pointer; letter-spacing: .01em; transition: background .15s; }}
    .btn-accept:hover {{ background: #178A65; }}
    .btn-decline {{ display: block; width: 100%; padding: 14px; background: #F3F4F6; color: #374151; border: none; border-radius: 10px; font-size: 15px; font-weight: 500; cursor: pointer; transition: background .15s; margin-top: 10px; }}
    .btn-decline:hover {{ background: #E5E7EB; }}
    .btn-cal {{ display: block; width: 100%; padding: 13px; background: transparent; color: #534AB7; border: 1.5px solid #AFA9EC; border-radius: 10px; font-size: 14px; font-weight: 500; cursor: pointer; transition: background .15s; margin-top: 10px; }}
    .btn-cal:hover {{ background: #EEEDFE; }}
    #confirm-section {{ display: none; }}
    .confirm-icon {{ width: 56px; height: 56px; border-radius: 50%; display: flex; align-items: center; justify-content: center; margin: 0 auto 20px; }}
    .footer-note {{ margin-top: 24px; font-size: 11px; color: #D1D5DB; text-align: center; letter-spacing: .08em; text-transform: uppercase; }}
  </style>
</head>
<body>
<div class="card">
  <!-- RSVP section -->
  <div id="rsvp-section">
    <div class="icon-circle">
      <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="#534AB7" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
        <rect x="3" y="4" width="18" height="18" rx="2" ry="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/>
      </svg>
    </div>
    <p class="club-label">GAB Dining Club</p>
    <h1 class="headline">You're invited</h1>
    <p class="subline">{contact_name}</p>

    {status_note}

    <div class="details-card">
      <div class="detail-row">
        <div class="detail-icon">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#6B7280" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2L2 7l10 5 10-5-10-5z"/><path d="M2 17l10 5 10-5"/><path d="M2 12l10 5 10-5"/></svg>
        </div>
        <div>
          <div class="detail-label">What</div>
          <div class="detail-value">{event_name}</div>
        </div>
      </div>
      <div class="detail-row">
        <div class="detail-icon">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#6B7280" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="4" width="18" height="18" rx="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>
        </div>
        <div>
          <div class="detail-label">When</div>
          <div class="detail-value">{date_str}</div>
        </div>
      </div>
      <div class="detail-row">
        <div class="detail-icon">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#6B7280" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/><circle cx="12" cy="10" r="3"/></svg>
        </div>
        <div>
          <div class="detail-label">Where</div>
          <div class="detail-value">{location_str}</div>
        </div>
      </div>
      <div class="detail-row">
        <div class="detail-icon">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#6B7280" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>
        </div>
        <div>
          <div class="detail-label">Going</div>
          <div class="detail-value">{going_text}</div>
        </div>
      </div>
    </div>

    <button class="btn-accept" onclick="respond('accept')">Accept invitation</button>
    <button class="btn-decline" onclick="respond('decline')">Decline</button>
  </div>

  <!-- Confirmation section (shown in-place after response) -->
  <div id="confirm-section">
    <div class="confirm-icon" id="confirm-icon"></div>
    <p class="club-label">GAB Dining Club</p>
    <h1 class="headline" id="confirm-headline"></h1>
    <p class="subline" id="confirm-subtext"></p>
    <div id="confirm-details"></div>
    <button class="btn-cal" id="cal-btn" onclick="downloadICS()" style="display:none">
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:middle;margin-right:6px"><rect x="3" y="4" width="18" height="18" rx="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>
      Add to calendar
    </button>
  </div>

  <p class="footer-note">With love · GAB Dining Club</p>
</div>

<script>
const TOKEN = {repr(token)};
const EVENT_NAME = {repr(event_name)};
const EVENT_DATE_ISO = {repr(event_date_iso)};
const EVENT_LOCATION = {repr(location_str)};

async function respond(action) {{
  const btn = action === 'accept'
    ? document.querySelector('.btn-accept')
    : document.querySelector('.btn-decline');
  btn.disabled = true;
  btn.textContent = action === 'accept' ? 'Accepting…' : 'Declining…';

  try {{
    const r = await fetch(`/rsvp/${{TOKEN}}/respond?action=${{action}}`, {{ method: 'POST' }});
    if (!r.ok) throw new Error('Server error');
    showConfirmation(action);
  }} catch(e) {{
    btn.disabled = false;
    btn.textContent = action === 'accept' ? 'Accept invitation' : 'Decline';
    alert('Something went wrong. Please try again.');
  }}
}}

function showConfirmation(action) {{
  document.getElementById('rsvp-section').style.display = 'none';
  const cs = document.getElementById('confirm-section');
  cs.style.display = 'block';

  if (action === 'accept') {{
    document.getElementById('confirm-icon').style.background = '#D1FAE5';
    document.getElementById('confirm-icon').innerHTML = `<svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="#059669" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>`;
    document.getElementById('confirm-headline').textContent = "See you there!";
    document.getElementById('confirm-subtext').textContent = "Your RSVP has been recorded. We look forward to having you at the table.";
    document.getElementById('cal-btn').style.display = 'block';
  }} else {{
    document.getElementById('confirm-icon').style.background = '#FEE2E2';
    document.getElementById('confirm-icon').innerHTML = `<svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="#DC2626" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>`;
    document.getElementById('confirm-headline').textContent = "We'll miss you";
    document.getElementById('confirm-subtext').textContent = "Thanks for letting us know. Hope to have you at the next one.";
  }}
}}

function downloadICS() {{
  if (!EVENT_DATE_ISO) return;
  const start = new Date(EVENT_DATE_ISO);
  const end = new Date(start.getTime() + 2 * 60 * 60 * 1000); // +2h
  const fmt = d => d.toISOString().replace(/[-:]/g, '').split('.')[0] + 'Z';
  const ics = [
    'BEGIN:VCALENDAR',
    'VERSION:2.0',
    'PRODID:-//GAB Dining Club//RSVP//EN',
    'BEGIN:VEVENT',
    `UID:${{TOKEN}}@gab.club`,
    `DTSTART:${{fmt(start)}}`,
    `DTEND:${{fmt(end)}}`,
    `SUMMARY:${{EVENT_NAME}}`,
    `LOCATION:${{EVENT_LOCATION}}`,
    'END:VEVENT',
    'END:VCALENDAR'
  ].join('\\r\\n');
  const blob = new Blob([ics], {{ type: 'text/calendar' }});
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = 'event.ics';
  a.click();
  URL.revokeObjectURL(a.href);
}}
</script>
</body>
</html>"""
    return HTMLResponse(html)


def _confirmation_page(headline: str, body_html: str) -> HTMLResponse:
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{headline} — GAB Dining Club</title>
</head>
<body style="background:#0f0f0f;margin:0;padding:40px 20px;font-family:Georgia,serif;min-height:100vh;display:flex;align-items:flex-start;justify-content:center;">
  <div style="background:linear-gradient(160deg,#1e1408,#120d04);border:1px solid #2e2818;border-radius:10px;padding:40px 44px;max-width:480px;width:100%;">
    <p style="margin:0 0 4px;font-size:9px;letter-spacing:.24em;text-transform:uppercase;color:#5a4e38;">GAB DINING CLUB</p>
    <h1 style="margin:10px 0 24px;font-size:28px;font-weight:normal;color:#d4aa4a;">{headline}</h1>
    {body_html}
    <p style="margin:28px 0 0;font-size:10px;color:#3a3020;text-align:center;letter-spacing:.1em;">WITH LOVE · GAB DINING CLUB</p>
  </div>
</body>
</html>"""
    return HTMLResponse(html)
