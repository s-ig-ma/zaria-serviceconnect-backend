# migrate_location.py
# ─────────────────────────────────────────────────────────────────────────────
# Run this ONCE to add latitude/longitude columns to existing database.
# This will NOT delete any existing data.
#
# Run it from the backend folder with:
#   python migrate_location.py
# ─────────────────────────────────────────────────────────────────────────────

import sqlite3
import os

# Find the database file
DB_PATH = "zaria_serviceconnect.db"

if not os.path.exists(DB_PATH):
    print(f"Database not found at {DB_PATH}")
    print("Make sure you run this from the backend folder.")
    exit(1)

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# Check which columns already exist
cursor.execute("PRAGMA table_info(providers)")
existing_columns = [row[1] for row in cursor.fetchall()]
print(f"Existing provider columns: {existing_columns}")

# Add latitude column if it doesn't exist
if "latitude" not in existing_columns:
    cursor.execute("ALTER TABLE providers ADD COLUMN latitude REAL")
    print("✅ Added 'latitude' column to providers table")
else:
    print("ℹ️  'latitude' column already exists — skipping")

# Add longitude column if it doesn't exist
if "longitude" not in existing_columns:
    cursor.execute("ALTER TABLE providers ADD COLUMN longitude REAL")
    print("✅ Added 'longitude' column to providers table")
else:
    print("ℹ️  'longitude' column already exists — skipping")

conn.commit()
conn.close()

print("\n✅ Migration complete. No data was lost.")
print("You can now restart the backend: uvicorn main:app --reload --host 0.0.0.0")
