import sys
import os
import tempfile
import pytest
from dotenv import load_dotenv

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import app as flask_app, get_db
from create_db import create_tables

load_dotenv(dotenv_path="test.env")

@pytest.fixture
def app():
    db_fd, db_path = tempfile.mkstemp()
    flask_app.config['DATABASE'] = db_path
    flask_app.config['TESTING'] = True

    with flask_app.app_context():
        db = get_db()
        create_tables(db)
        yield flask_app

    os.close(db_fd)
    os.unlink(db_path)

@pytest.fixture
def client(app):
    return app.test_client()