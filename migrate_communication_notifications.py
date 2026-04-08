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

    if not table_exists(cursor, "messages"):
        cursor.execute(
            """
            CREATE TABLE messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                complaint_id INTEGER,
                sender_user_id INTEGER NOT NULL,
                recipient_user_id INTEGER NOT NULL,
                content TEXT NOT NULL,
                is_read BOOLEAN NOT NULL DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (complaint_id) REFERENCES complaints (id),
                FOREIGN KEY (sender_user_id) REFERENCES users (id),
                FOREIGN KEY (recipient_user_id) REFERENCES users (id)
            )
            """
        )

    if not table_exists(cursor, "complaint_actions"):
        cursor.execute(
            """
            CREATE TABLE complaint_actions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                complaint_id INTEGER NOT NULL,
                admin_user_id INTEGER NOT NULL,
                target_user_id INTEGER,
                action_type TEXT NOT NULL,
                note TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (complaint_id) REFERENCES complaints (id),
                FOREIGN KEY (admin_user_id) REFERENCES users (id),
                FOREIGN KEY (target_user_id) REFERENCES users (id)
            )
            """
        )

    if not table_exists(cursor, "notifications"):
        cursor.execute(
            """
            CREATE TABLE notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                message TEXT NOT NULL,
                type TEXT NOT NULL DEFAULT 'general',
                related_id INTEGER,
                is_read BOOLEAN NOT NULL DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
            """
        )

    cursor.execute("CREATE INDEX IF NOT EXISTS ix_messages_complaint_id ON messages (complaint_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS ix_messages_recipient_user_id ON messages (recipient_user_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS ix_complaint_actions_complaint_id ON complaint_actions (complaint_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS ix_notifications_user_id ON notifications (user_id)")

    connection.commit()
    connection.close()
    print("Communication and notification migration completed.")


if __name__ == "__main__":
    main()
