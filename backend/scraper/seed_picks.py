"""
Seed realistic member recommendations to make the map alive.
Run once: python -m backend.scraper.seed_picks
"""
import asyncio
import random
import sys
from datetime import datetime, timedelta
from sqlalchemy import text
from backend.database import SessionLocal

MEMBERS = [
    {"name": "Sofia Marchetti",  "email": "sofia@example.com",  "type": "member", "tags": ["regular", "italy-obsessed"]},
    {"name": "James Okonkwo",    "email": "james@example.com",   "type": "member", "tags": ["regular", "wine"]},
    {"name": "Priya Nair",       "email": "priya@example.com",   "type": "member", "tags": ["regular", "spice-hunter"]},
    {"name": "Marcus Chen",      "email": "marcus@example.com",  "type": "member", "tags": ["regular", "noodles"]},
    {"name": "Amara Diallo",     "email": "amara@example.com",   "type": "member", "tags": ["regular"]},
    {"name": "Leo Bergström",    "email": "leo@example.com",     "type": "member", "tags": ["regular", "brunch"]},
    {"name": "Yasmin Torres",    "email": "yasmin@example.com",  "type": "member", "tags": ["regular", "date-night"]},
    {"name": "Rafi Cohen",       "email": "rafi@example.com",    "type": "member", "tags": ["regular"]},
]

# (cuisine_fragment, notes_pool, tags_pool, score_range)
CUISINE_PICKS = {
    "Thai": (
        ["Unreal pad see ew, they actually char it properly", "Fish sauce balance was perfect", "Ask for it Thai spicy, not tourist spicy", "Khao soi was legit northern-style", "Som tum had the right funky fermented kick"],
        ["authentic", "spicy", "date-night", "lunch", "noodles"],
        (7, 10),
    ),
    "Korean": (
        ["Best banchan spread in the city", "The galbi jjim was falling off the bone", "Late-night spot, open till 2am", "KBBQ — get the beef belly", "Sundubu jjigae better than Koreatown"],
        ["bbq", "late-night", "group", "authentic", "comfort"],
        (7, 10),
    ),
    "Chinese": (
        ["Shanghai dumplings, no queue if you go at 11:30", "Cantonese roast duck — bring cash", "Hand-pulled noodles done tableside", "Dim sum on weekday mornings is the move", "XLB here rival Joe's Shanghai"],
        ["dumplings", "dim-sum", "group", "authentic", "noodles"],
        (7, 10),
    ),
    "Italian": (
        ["Pasta is all fresh, no shortcuts", "Roman-style — thin crust, crispy base", "The cacio e pepe is the real deal, no cream", "Sunday gravy situation — go early", "Barolo list is serious"],
        ["pasta", "wine", "date-night", "romantic", "classic"],
        (7, 10),
    ),
    "Mexican": (
        ["Birria tacos with proper consommé", "Mezcal selection is excellent", "Mole negro from Oaxaca, not Tex-Mex", "Carnitas — order by the pound", "Al pastor off the trompo"],
        ["tacos", "mezcal", "casual", "authentic", "lunch"],
        (7, 10),
    ),
    "Japanese": (
        ["Omakase counter — book 3 weeks out", "Ramen broth simmered 18hrs minimum", "Izakaya vibes, order the karaage", "Sushi rice temp was actually correct", "Tonkotsu ramen at midnight — iconic"],
        ["sushi", "ramen", "date-night", "late-night", "omakase"],
        (7, 10),
    ),
    "French": (
        ["Proper Burgundy wine list", "Duck confit like Paris bistros", "Pre-theatre prix fixe is great value", "Soufflé takes 25min — worth it", "Neighborhood gem, no tourists"],
        ["classic", "wine", "date-night", "romantic", "bistro"],
        (7, 10),
    ),
    "Vietnamese": (
        ["Pho broth is clear and deep — good sign", "Bahn mi on fresh-baked bread", "Bun bo hue over pho if you want heat", "Bo luc lac — the shaking beef is excellent", "Family-run, been here 20 years"],
        ["pho", "authentic", "lunch", "cheap-eat", "noodles"],
        (6, 9),
    ),
    "Indian": (
        ["Butter chicken is secondary — go for the dal makhani", "Jackson Heights spot, legit Punjabi", "Dosa crispy and enormous", "They do proper Hyderabadi biryani", "Lunch thali is incredible value"],
        ["spicy", "vegetarian", "lunch", "authentic", "group"],
        (7, 10),
    ),
    "Mediterranean": (
        ["Whole grilled fish done simply — perfect", "Hummus made in-house, smooth", "Mezze for the table, order everything", "Lebanese — the kibbeh is excellent", "Greek — order the lamb chops"],
        ["mezze", "group", "healthy", "wine", "date-night"],
        (7, 9),
    ),
    "default": (
        ["Solid neighbourhood spot", "Worth the trip", "Good value for the quality", "One of the better ones in the area", "Regulars know to go here"],
        ["casual", "local", "lunch", "neighbourhood"],
        (6, 9),
    ),
}

def _pick_cuisine_data(cuisine_raw):
    if not cuisine_raw:
        return CUISINE_PICKS["default"]
    c = cuisine_raw.lower()
    for key in CUISINE_PICKS:
        if key.lower() in c:
            return CUISINE_PICKS[key]
    return CUISINE_PICKS["default"]

def _random_date_ago(max_days=180):
    delta = random.randint(1, max_days)
    return datetime.utcnow() - timedelta(days=delta)


async def seed_picks():
    async with SessionLocal() as db:
        # Check if already seeded
        existing = (await db.execute(text("SELECT COUNT(*) FROM contacts WHERE type='member'"))).scalar()
        if existing >= len(MEMBERS):
            print(f"Already have {existing} members — skipping member creation")
            member_ids = [row[0] for row in (await db.execute(text("SELECT id FROM contacts WHERE type='member' LIMIT 20"))).fetchall()]
        else:
            # Insert members
            member_ids = []
            for m in MEMBERS:
                tags_json = str(m["tags"]).replace("'", '"')
                now = datetime.utcnow().isoformat()
                result = await db.execute(text(
                    "INSERT INTO contacts (name, email, type, tags, active, created_at) VALUES (:name, :email, :type, :tags, 1, :created_at)"
                ), {"name": m["name"], "email": m["email"], "type": m["type"], "tags": tags_json, "created_at": now})
                member_ids.append(result.lastrowid)
            await db.commit()
            print(f"Created {len(member_ids)} members")

        # Get restaurants with borough spread
        rows = (await db.execute(text("""
            SELECT id, name, borough, cuisine_raw FROM restaurants
            WHERE borough IS NOT NULL
            ORDER BY RANDOM()
            LIMIT 300
        """))).fetchall()

        # Check existing recommendations
        existing_recs = (await db.execute(text("SELECT COUNT(*) FROM recommendations"))).scalar()
        if existing_recs > 50:
            print(f"Already have {existing_recs} recommendations — skipping")
            return

        # Create 80-120 realistic picks
        # Weight: each member picks 10-15 restaurants they've been to
        inserted = 0
        used_pairs = set()

        # Shuffle and assign
        restaurant_pool = list(rows)
        random.shuffle(restaurant_pool)

        picks_per_member = len(restaurant_pool) // len(member_ids)

        for i, member_id in enumerate(member_ids):
            # Each member gets a slice of restaurants + some random overlap
            start = i * (picks_per_member // 2)
            my_restaurants = restaurant_pool[start:start + random.randint(10, 18)]

            for rest_id, rest_name, borough, cuisine_raw in my_restaurants:
                if (member_id, rest_id) in used_pairs:
                    continue
                used_pairs.add((member_id, rest_id))

                notes_pool, tags_pool, score_range = _pick_cuisine_data(cuisine_raw)
                score = round(random.uniform(*score_range), 1)
                notes = random.choice(notes_pool) if random.random() > 0.25 else None
                tags = random.sample(tags_pool, k=random.randint(1, min(3, len(tags_pool))))
                visited = _random_date_ago(180)
                tags_json = str(tags).replace("'", '"')

                await db.execute(text("""
                    INSERT INTO recommendations
                    (restaurant_id, contact_id, rating, notes, tags, visited_at, created_at)
                    VALUES (:rid, :cid, :rating, :notes, :tags, :visited, :created)
                """), {
                    "rid": rest_id, "cid": member_id,
                    "rating": score, "notes": notes,
                    "tags": tags_json, "visited": visited, "created": visited,
                })
                inserted += 1

        await db.commit()
        print(f"Inserted {inserted} recommendations across {len(used_pairs)} restaurant-member pairs")
        print("Done! Refresh the map to see activity.")


if __name__ == "__main__":
    asyncio.run(seed_picks())
