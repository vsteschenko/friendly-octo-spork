import sqlite3

def create_tables(db):
    cursor = db.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT NOT NULL,
            password TEXT NOT NULL,
            is_verified BOOLEAN DEFAULT 0,
            verification_token TEXT
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            amount REAL,
            timestamp TEXT,
            category TEXT,
            type TEXT,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    ''')

    db.commit()