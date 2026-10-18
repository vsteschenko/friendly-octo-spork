-- Full database schema. Applied automatically on startup (see db.py).
-- Every statement uses IF NOT EXISTS, so running it on an existing database
-- never changes or deletes existing tables or data.

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT NOT NULL,
    password TEXT NOT NULL,
    is_verified BOOLEAN DEFAULT 0,
    verification_token TEXT,
    verification_token_expires_at TEXT,
    reset_token TEXT,
    reset_token_expires_at TEXT,
    delete_token TEXT,
    delete_token_expires_at TEXT
);

CREATE TABLE IF NOT EXISTS transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    amount REAL,
    timestamp TEXT,
    category TEXT,
    type TEXT,
    place TEXT,
    comment TEXT,
    FOREIGN KEY(user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS login_attempts (
    email TEXT,
    ip TEXT,
    timestamp TEXT,
    success INTEGER
);

-- Generic counter for rate limits (signup emails, password reset emails, ...)
CREATE TABLE IF NOT EXISTS rate_events (
    action TEXT NOT NULL,
    key TEXT NOT NULL,
    timestamp TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_rate_events_lookup ON rate_events(action, key, timestamp);
CREATE INDEX IF NOT EXISTS idx_login_attempts_ts ON login_attempts(timestamp);
CREATE INDEX IF NOT EXISTS idx_transactions_user_ts ON transactions(user_id, timestamp);
