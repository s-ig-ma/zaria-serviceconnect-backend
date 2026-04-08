"""
Run this ONCE to add product-fix fields for verification, addresses, and booking flow.

Usage:
  python migrate_product_fixes.py
"""

import os
import sqlite3


DB_PATH = "zaria_serviceconnect.db"


def add_column(cursor, table_name, column_name, ddl):
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = [row[1] for row in cursor.fetchall()]
    if column_name in columns:
        print(f"- {table_name}.{column_name} already exists")
        return
    cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {ddl}")
    print(f"- Added {table_name}.{column_name}")


if not os.path.exists(DB_PATH):
    print(f"Database not found at {DB_PATH}")
    print("Run this from the backend folder.")
    raise SystemExit(1)

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

add_column(cursor, "users", "home_address", "home_address VARCHAR(255)")
add_column(cursor, "providers", "passport_photo_path", "passport_photo_path VARCHAR(255)")
add_column(cursor, "providers", "skill_proof_path", "skill_proof_path VARCHAR(255)")
add_column(cursor, "providers", "has_shop_in_zaria", "has_shop_in_zaria BOOLEAN DEFAULT 0")
add_column(cursor, "providers", "shop_address", "shop_address VARCHAR(255)")
add_column(cursor, "bookings", "service_address", "service_address VARCHAR(255)")

cursor.execute(
    """
    UPDATE users
    SET home_address = location
    WHERE (home_address IS NULL OR TRIM(home_address) = '')
      AND location IS NOT NULL
      AND TRIM(location) != ''
    """
)
print("- Backfilled users.home_address from users.location where possible")

conn.commit()
conn.close()

print("\nMigration complete. No data was deleted.")
print("Restart the backend after running this script.")
