from datetime import datetime
from typing import Optional
from sqlalchemy import (
    Integer, String, Float, Text, DateTime, ForeignKey,
    Boolean, JSON, func
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.database import Base


# ─── Cuisine ────────────────────────────────────────────────────────────────

class Cuisine(Base):
    __tablename__ = "cuisines"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    region: Mapped[str] = mapped_column(String(100))          # e.g. "Southeast Asia"
    sub_region: Mapped[Optional[str]] = mapped_column(String(100))  # e.g. "Northern Thailand"
    description: Mapped[Optional[str]] = mapped_column(Text)
    key_ingredients: Mapped[Optional[str]] = mapped_column(JSON)    # list of strings
    key_techniques: Mapped[Optional[str]] = mapped_column(JSON)
    flavor_profile: Mapped[Optional[str]] = mapped_column(JSON)     # {"spicy": 4, "umami": 3, ...}
    typical_dishes: Mapped[Optional[str]] = mapped_column(JSON)
    differentiating_factors: Mapped[Optional[str]] = mapped_column(Text)  # what makes this distinct from similar cuisines
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())

    restaurants: Mapped[list["Restaurant"]] = relationship(back_populates="cuisine")


# ─── Restaurant ─────────────────────────────────────────────────────────────

class Restaurant(Base):
    __tablename__ = "restaurants"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    address: Mapped[Optional[str]] = mapped_column(String(400))
    city: Mapped[Optional[str]] = mapped_column(String(100))
    country: Mapped[Optional[str]] = mapped_column(String(100))
    neighborhood: Mapped[Optional[str]] = mapped_column(String(100))
    borough: Mapped[Optional[str]] = mapped_column(String(50))
    lat: Mapped[Optional[float]] = mapped_column(Float)
    lng: Mapped[Optional[float]] = mapped_column(Float)
    cuisine_id: Mapped[Optional[int]] = mapped_column(ForeignKey("cuisines.id"))
    cuisine_raw: Mapped[Optional[str]] = mapped_column(String(200))  # raw tag from source
    rating: Mapped[Optional[float]] = mapped_column(Float)
    price_level: Mapped[Optional[int]] = mapped_column(Integer)      # 1-4
    phone: Mapped[Optional[str]] = mapped_column(String(50))
    website: Mapped[Optional[str]] = mapped_column(String(500))
    menu_url: Mapped[Optional[str]] = mapped_column(String(500))
    google_place_id: Mapped[Optional[str]] = mapped_column(String(200), unique=True)
    yelp_id: Mapped[Optional[str]] = mapped_column(String(200))
    source: Mapped[Optional[str]] = mapped_column(String(50))        # "google" | "yelp" | "manual"
    notes: Mapped[Optional[str]] = mapped_column(Text)
    photo_url: Mapped[Optional[str]] = mapped_column(String(1000))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now())

    cuisine: Mapped[Optional["Cuisine"]] = relationship(back_populates="restaurants")
    menus: Mapped[list["Menu"]] = relationship(back_populates="restaurant")
    recommendations: Mapped[list["Recommendation"]] = relationship(back_populates="restaurant")
    contacts: Mapped[list["Contact"]] = relationship(back_populates="restaurant")
    events: Mapped[list["Event"]] = relationship(back_populates="restaurant")


# ─── Menu ────────────────────────────────────────────────────────────────────

class Menu(Base):
    __tablename__ = "menus"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    restaurant_id: Mapped[int] = mapped_column(ForeignKey("restaurants.id"), nullable=False)
    source_url: Mapped[Optional[str]] = mapped_column(String(500))
    source_type: Mapped[Optional[str]] = mapped_column(String(50))   # "url" | "pdf" | "manual"
    raw_text: Mapped[Optional[str]] = mapped_column(Text)
    cuisine_match: Mapped[Optional[str]] = mapped_column(JSON)       # AI analysis result
    ingested_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())

    restaurant: Mapped["Restaurant"] = relationship(back_populates="menus")
    items: Mapped[list["MenuItem"]] = relationship(back_populates="menu", cascade="all, delete-orphan")


class MenuItem(Base):
    __tablename__ = "menu_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    menu_id: Mapped[int] = mapped_column(ForeignKey("menus.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    price: Mapped[Optional[float]] = mapped_column(Float)
    category: Mapped[Optional[str]] = mapped_column(String(100))     # "starter" | "main" | "dessert"
    embedding: Mapped[Optional[str]] = mapped_column(JSON)           # list[float]

    menu: Mapped["Menu"] = relationship(back_populates="items")


# ─── CRM ─────────────────────────────────────────────────────────────────────

class Contact(Base):
    __tablename__ = "contacts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    type: Mapped[str] = mapped_column(String(50), default="member")  # "member" | "restaurant" | "vendor"
    email: Mapped[Optional[str]] = mapped_column(String(200))
    phone: Mapped[Optional[str]] = mapped_column(String(50))
    restaurant_id: Mapped[Optional[int]] = mapped_column(ForeignKey("restaurants.id"))
    tags: Mapped[Optional[str]] = mapped_column(JSON)                # list of strings
    notes: Mapped[Optional[str]] = mapped_column(Text)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())

    restaurant: Mapped[Optional["Restaurant"]] = relationship(back_populates="contacts")
    invites: Mapped[list["EventInvite"]] = relationship(back_populates="contact")
    recommendations: Mapped[list["Recommendation"]] = relationship(back_populates="contact")
    outreach_log: Mapped[list["OutreachLog"]] = relationship(back_populates="contact")


class Event(Base):
    __tablename__ = "events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(300), nullable=False)
    date: Mapped[Optional[datetime]] = mapped_column(DateTime)
    location: Mapped[Optional[str]] = mapped_column(String(400))
    restaurant_id: Mapped[Optional[int]] = mapped_column(ForeignKey("restaurants.id"))
    description: Mapped[Optional[str]] = mapped_column(Text)
    max_guests: Mapped[Optional[int]] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(50), default="draft")  # draft|confirmed|completed|cancelled
    reminder_sent: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())

    restaurant: Mapped[Optional["Restaurant"]] = relationship(back_populates="events")
    invites: Mapped[list["EventInvite"]] = relationship(back_populates="event", cascade="all, delete-orphan")


class EventInvite(Base):
    __tablename__ = "event_invites"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    event_id: Mapped[int] = mapped_column(ForeignKey("events.id"), nullable=False)
    contact_id: Mapped[int] = mapped_column(ForeignKey("contacts.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="invited")  # invited|accepted|declined|attended
    rsvp_token: Mapped[Optional[str]] = mapped_column(String(64), unique=True)
    sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    responded_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    notes: Mapped[Optional[str]] = mapped_column(Text)

    event: Mapped["Event"] = relationship(back_populates="invites")
    contact: Mapped["Contact"] = relationship(back_populates="invites")


class OutreachTemplate(Base):
    __tablename__ = "outreach_templates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    type: Mapped[str] = mapped_column(String(50))  # "invite" | "followup" | "welcome" | "custom"
    subject: Mapped[str] = mapped_column(String(400))
    body: Mapped[str] = mapped_column(Text)          # Jinja2 template
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())

    log: Mapped[list["OutreachLog"]] = relationship(back_populates="template")


class OutreachLog(Base):
    __tablename__ = "outreach_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    contact_id: Mapped[int] = mapped_column(ForeignKey("contacts.id"), nullable=False)
    template_id: Mapped[Optional[int]] = mapped_column(ForeignKey("outreach_templates.id"))
    subject: Mapped[Optional[str]] = mapped_column(String(400))
    body: Mapped[Optional[str]] = mapped_column(Text)
    sent_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    status: Mapped[str] = mapped_column(String(50), default="sent")  # sent|failed|opened

    contact: Mapped["Contact"] = relationship(back_populates="outreach_log")
    template: Mapped[Optional["OutreachTemplate"]] = relationship(back_populates="log")


# ─── Recommendations ─────────────────────────────────────────────────────────

class Recommendation(Base):
    __tablename__ = "recommendations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    restaurant_id: Mapped[int] = mapped_column(ForeignKey("restaurants.id"), nullable=False)
    contact_id: Mapped[Optional[int]] = mapped_column(ForeignKey("contacts.id"))
    rating: Mapped[Optional[float]] = mapped_column(Float)    # 1-10
    notes: Mapped[Optional[str]] = mapped_column(Text)
    tags: Mapped[Optional[str]] = mapped_column(JSON)         # ["date night", "business lunch"]
    visited_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())

    restaurant: Mapped["Restaurant"] = relationship(back_populates="recommendations")
    contact: Mapped[Optional["Contact"]] = relationship(back_populates="recommendations")
