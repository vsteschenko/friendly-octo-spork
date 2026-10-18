import os
import sqlite3
from flask import g, current_app

SCHEMA_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "schema.sql")
_initialized_paths = set()


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
        if path not in _initialized_paths:
            init_db(db)
            _initialized_paths.add(path)
    return db
