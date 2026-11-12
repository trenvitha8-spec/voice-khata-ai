
import sqlite3
from pathlib import Path

# Find the main project folder
BASE_DIR = Path(__file__).resolve().parent.parent

# Database and schema locations
DB_PATH = BASE_DIR / "database" / "voice_khata.db"
SCHEMA_PATH = BASE_DIR / "database" / "schema.sql"


def get_db_connection():
    """Create a connection to the SQLite database."""
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def initialize_database():
    """Create all database tables using schema.sql."""

    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    connection = get_db_connection()

    try:
        with open(SCHEMA_PATH, "r", encoding="utf-8") as file:
            schema = file.read()

        connection.executescript(schema)
        connection.commit()

        print("Database initialized successfully!")

    finally:
        connection.close()


if __name__ == "__main__":
    initialize_database()
