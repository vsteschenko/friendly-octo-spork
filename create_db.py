"""Create (or upgrade) the database at the path in $DATABASE.

The app also does this automatically on startup, so running this script is optional.
"""
import os
import sqlite3
from dotenv import load_dotenv
from db import init_db


def create_tables(db):
    init_db(db)


if __name__ == "__main__":
    load_dotenv()
    path = os.getenv("DATABASE")
    if not path:
        raise SystemExit("Set DATABASE in your .env first")
    con = sqlite3.connect(path)
    create_tables(con)
    con.close()
    print(f"Database ready at {path}")
