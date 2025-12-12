from datetime import datetime, timedelta
import secrets

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