import os
import sqlite3
from flask import g, current_app

SCHEMA_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "schema.sql")


def init_db(db):
    """Create any missing tables/indexes. Safe to run on an existing database."""
    with open(SCHEMA_PATH) as f:
        db.executescript(f.read())
    db.commit()


def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        path = current_app.config["DATABASE"]
        db = g._database = sqlite3.connect(path)
        # Cheap (every statement is IF NOT EXISTS) and always correct, even if
        # the database file is replaced while the app is running.
        init_db(db)
    return db
