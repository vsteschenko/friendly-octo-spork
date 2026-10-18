import os
import sys

# Settings must exist before the app is imported.
os.environ.setdefault("SECRET_KEY", "test-secret")
os.environ.setdefault("BCRYPT_ROUNDS", "4")  # fast hashing in tests
os.environ.setdefault("DATABASE", ":memory:")
os.environ.setdefault("FLASK_ENV", "development")

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
