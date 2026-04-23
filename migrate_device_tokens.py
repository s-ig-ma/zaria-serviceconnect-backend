import sqlite3
from pathlib import Path


DB_PATH = Path(__file__).resolve().parent / "zaria_serviceconnect.db"


def table_exists(cursor, table_name: str) -> bool:
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (table_name,),
    )
    return cursor.fetchone() is not None


def main():
    connection = sqlite3.connect(DB_PATH)
    cursor = connection.cursor()

    if not table_exists(cursor, "device_tokens"):
        cursor.execute(
            """
            CREATE TABLE device_tokens (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                token TEXT NOT NULL UNIQUE,
                platform TEXT NOT NULL DEFAULT 'android',
                device_name TEXT,
                is_active BOOLEAN NOT NULL DEFAULT 1,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                last_seen_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
            """
        )

    cursor.execute("CREATE INDEX IF NOT EXISTS ix_device_tokens_user_id ON device_tokens (user_id)")
    cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS ix_device_tokens_token ON device_tokens (token)")

    connection.commit()
    connection.close()
    print("Device token migration completed.")


if __name__ == "__main__":
    main()
