"""
Run this ONCE to support Feature 7: Flexible Service System.

Usage:
  python migrate_flexible_service.py
"""

import sqlite3
from pathlib import Path


DB_PATH = Path(__file__).resolve().parent / "zaria_serviceconnect.db"


def main():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("PRAGMA table_info(providers)")
    columns = cursor.fetchall()
    column_names = [col[1] for col in columns]
    has_service_name = "service_name" in column_names
    category_not_null = any(col[1] == "category_id" and col[3] == 1 for col in columns)

    print(f"Current provider columns: {column_names}")
    print(f"category_id NOT NULL: {category_not_null}")

    if has_service_name and not category_not_null:
        print("Flexible service migration already applied.")
        conn.close()
        return

    cursor.execute("PRAGMA foreign_keys=OFF")

    try:
        cursor.execute(
            """
            CREATE TABLE providers_new (
                id INTEGER NOT NULL PRIMARY KEY,
                user_id INTEGER NOT NULL UNIQUE,
                category_id INTEGER,
                service_name VARCHAR(150),
                description TEXT,
                years_of_experience INTEGER,
                id_document_path VARCHAR(255),
                status VARCHAR(9),
                average_rating FLOAT,
                total_reviews INTEGER,
                location VARCHAR(200),
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME,
                latitude REAL,
                longitude REAL,
                availability_status VARCHAR(20) NOT NULL DEFAULT 'available',
                FOREIGN KEY(user_id) REFERENCES users (id),
                FOREIGN KEY(category_id) REFERENCES categories (id)
            )
            """
        )

        select_service_name = (
            "service_name" if has_service_name else "NULL AS service_name"
        )

        cursor.execute(
            f"""
            INSERT INTO providers_new (
                id, user_id, category_id, service_name, description,
                years_of_experience, id_document_path, status,
                average_rating, total_reviews, location,
                created_at, updated_at, latitude, longitude, availability_status
            )
            SELECT
                id, user_id, category_id, {select_service_name}, description,
                years_of_experience, id_document_path, status,
                average_rating, total_reviews, location,
                created_at, updated_at, latitude, longitude, availability_status
            FROM providers
            """
        )

        cursor.execute("DROP TABLE providers")
        cursor.execute("ALTER TABLE providers_new RENAME TO providers")
        cursor.execute("CREATE INDEX ix_providers_id ON providers (id)")
        conn.commit()
        print("Migration completed successfully.")
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.execute("PRAGMA foreign_keys=ON")
        conn.close()


if __name__ == "__main__":
    main()
