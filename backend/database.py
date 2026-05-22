from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import text
from backend.config import get_settings

settings = get_settings()

engine = create_async_engine(settings.database_url, echo=False)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncSession:
    async with SessionLocal() as session:
        yield session


# Columns to ensure exist: (table, column, sql_type, default)
_MIGRATIONS = [
    ("events",       "reminder_sent", "BOOLEAN",     "0"),
    ("event_invites","rsvp_token",    "VARCHAR(64)",  "NULL"),
    ("restaurants",  "neighborhood",       "VARCHAR(100)", "NULL"),
    ("restaurants",  "borough",            "VARCHAR(50)",  "NULL"),
    ("restaurants",  "photo_url",          "VARCHAR(1000)","NULL"),
    ("cuisines",     "differentiating_factors", "TEXT",    "NULL"),
]

_BOROUGH_KEYWORDS = {
    "Brooklyn":      ["brooklyn", " bk "],
    "Queens":        ["queens", "astoria", "flushing", "jackson heights",
                      "forest hills", "jamaica", "long island city", "lic",
                      "sunnyside", "woodside", "elmhurst", "corona"],
    "Bronx":         ["bronx"],
    "Staten Island": ["staten island"],
}


async def init_db():
    async with engine.begin() as conn:
        # Create all tables that don't exist yet
        await conn.run_sync(Base.metadata.create_all)

        # Safe column additions — ALTER TABLE IF NOT EXISTS equivalent for SQLite
        for table, column, col_type, default in _MIGRATIONS:
            existing = await conn.execute(text(f"PRAGMA table_info({table})"))
            cols = [row[1] for row in existing.fetchall()]
            if column not in cols:
                await conn.execute(
                    text(f"ALTER TABLE {table} ADD COLUMN {column} {col_type} DEFAULT {default}")
                )

        # Backfill borough for existing restaurants where it's not set
        rows = await conn.execute(
            text("SELECT id, address, city FROM restaurants WHERE borough IS NULL")
        )
        updates = []
        for row_id, address, city in rows.fetchall():
            combined = f"{address or ''} {city or ''}".lower()
            detected = None
            for borough, keywords in _BOROUGH_KEYWORDS.items():
                if any(kw in combined for kw in keywords):
                    detected = borough
                    break
            if detected is None and any(k in combined for k in ["new york", " ny ", "nyc", "manhattan"]):
                detected = "Manhattan"
            if detected:
                updates.append({"b": detected, "id": row_id})
        for u in updates:
            await conn.execute(text("UPDATE restaurants SET borough = :b WHERE id = :id"), u)
