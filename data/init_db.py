#!/usr/bin/env python3
"""Initialize the Mirage SQLite database."""

import sqlite3
import os
from pathlib import Path

DB_PATH = Path(__file__).parent / "mirage.db"
SCHEMA_PATH = Path(__file__).parent / "schema.sql"

def init_db():
    """Create the database and tables if they don't exist."""
    conn = sqlite3.connect(DB_PATH)

    with open(SCHEMA_PATH, 'r') as f:
        schema = f.read()

    conn.executescript(schema)
    conn.commit()
    conn.close()

    print(f"Database initialized at: {DB_PATH}")

if __name__ == "__main__":
    init_db()
