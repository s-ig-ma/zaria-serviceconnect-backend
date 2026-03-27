# migrate_availability.py
# ─────────────────────────────────────────────────────────────────────────────
# Run this ONCE to add availability_status column to existing database.
# This will NOT delete any existing data.
#
# Run from the backend folder:
#   python migrate_availability.py
# ─────────────────────────────────────────────────────────────────────────────

import sqlite3
import os

DB_PATH = "zaria_serviceconnect.db"

if not os.path.exists(DB_PATH):
    print(f"Database not found at {DB_PATH}")
    print("Make sure you run this from the backend folder.")
    exit(1)

conn   = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

cursor.execute("PRAGMA table_info(providers)")
existing_columns = [row[1] for row in cursor.fetchall()]
print(f"Existing provider columns: {existing_columns}")

if "availability_status" not in existing_columns:
    cursor.execute(
        "ALTER TABLE providers ADD COLUMN availability_status VARCHAR DEFAULT 'available'"
    )
    print("✅ Added 'availability_status' column to providers table")

    # Set all existing approved providers to available
    cursor.execute(
        "UPDATE providers SET availability_status = 'available' WHERE status = 'approved'"
    )
    print("✅ Set all approved providers to 'available'")
else:
    print("ℹ️  'availability_status' column already exists — skipping")

conn.commit()
conn.close()

print("\n✅ Migration complete. No data was lost.")
print("Restart the backend: uvicorn main:app --reload --host 0.0.0.0")
