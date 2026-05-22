from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from backend.database import init_db, SessionLocal
from backend.routers import restaurants, menus, cuisines, crm, map as map_router, rsvp
from rich.console import Console

console = Console()
scheduler = AsyncIOScheduler(timezone="America/New_York")


async def _run_reminders():
    """Scheduled job — runs every hour to send 24h-ahead event reminders."""
    from backend.crm.reminders import send_reminders
    async with SessionLocal() as db:
        try:
            await send_reminders(db)
        except Exception as e:
            console.print(f"[red]Reminder job error:[/] {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()

    # Seed reminder template if missing
    async with SessionLocal() as db:
        from backend.crm.reminders import REMINDER_TEMPLATE
        from backend.models import OutreachTemplate
        from sqlalchemy import select
        existing = await db.execute(
            select(OutreachTemplate).where(OutreachTemplate.name == REMINDER_TEMPLATE["name"])
        )
        if not existing.scalar_one_or_none():
            db.add(OutreachTemplate(**REMINDER_TEMPLATE))
            await db.commit()
            console.print("[green]Seeded reminder template[/]")

    # Start scheduler
    scheduler.add_job(_run_reminders, "interval", hours=1, id="reminders", replace_existing=True)
    scheduler.start()
    console.print("[green]Reminder scheduler started[/] — checking every hour")

    yield

    scheduler.shutdown()


app = FastAPI(
    title="GAB Dining Club API",
    description="Restaurant discovery, menu knowledge base, CRM, and dining events.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(restaurants.router)
app.include_router(menus.router)
app.include_router(cuisines.router)
app.include_router(crm.router)
app.include_router(map_router.router)
app.include_router(rsvp.router)


@app.get("/health")
async def health():
    return {"status": "ok", "service": "GAB Dining Club", "scheduler": scheduler.running}


@app.post("/reminders/run")
async def trigger_reminders():
    """Manually trigger the reminder job — useful for testing."""
    from backend.crm.reminders import send_reminders
    async with SessionLocal() as db:
        result = await send_reminders(db)
    return result


# Serve frontend — must be LAST so API routes take precedence
app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")
