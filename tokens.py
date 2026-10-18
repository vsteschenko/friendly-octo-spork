from datetime import datetime, timedelta
import secrets
import hashlib

def create_token_with_expiry(hours=1):
    token = generate_token()
    expires_at = (datetime.now() + timedelta(hours=hours)).isoformat()
    return token, expires_at

def is_token_expired(expires_at: str) -> bool:
    if not expires_at:
        return True
    try:
        expires_at = datetime.fromisoformat(expires_at)
    except ValueError:
        return True
    return datetime.now() > expires_at

def generate_token():
    return secrets.token_urlsafe(32)

def hash_token(token: str) -> str:
    """What we store in the database. The raw token only ever goes in the email,
    so someone who reads the database can't use the links."""
    return hashlib.sha256(token.encode('utf-8')).hexdigest()

def password_fingerprint(password_hash) -> str:
    """Short value stored in the session. It changes whenever the password
    changes, which logs out every other session."""
    if isinstance(password_hash, str):
        password_hash = password_hash.encode('utf-8')
    return hashlib.sha256(password_hash).hexdigest()[:32]