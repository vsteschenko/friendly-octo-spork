from email_validator import validate_email,EmailNotValidError
from flask import request, session, render_template, current_app
from db import get_db
from tokens import is_token_expired
from datetime import datetime, timedelta

def email_validator(email):
    try:
        validate_email(email, check_deliverability=False)
        return True
    except EmailNotValidError:
        return False

def password_validator(password: str):
    if not password:
        return False, "Password required"
    if len(password) < 10:
        return False, "Password must be at least 10 characters long"
    has_letter = any(ch.isalpha() for ch in password)
    has_digit = any(ch.isdigit() for ch in password)
    if not has_letter or not has_digit:
        return False, "Password must contain at least one letter and one digit"
    return True, None

def get_client_ip():
    # ProxyFix (app.py) already replaced remote_addr with the address nginx saw.
    # Never read X-Forwarded-For directly: the client controls that header.
    return request.remote_addr or "unknown"

def get_user_id(email):
    cur = get_db().cursor()
    cur.execute("SELECT id FROM users WHERE email = ?", (email,))
    row = cur.fetchone()
    cur.close()
    return row[0] if row else None

def is_rate_limited(email: str, ip: str, window_seconds: int = 300, max_attempts: int = 5,
                    ip_window_seconds: int = 900, ip_max_attempts: int = 20) -> bool:
    """Block login when one client keeps failing.

    Limits are per (email, IP) pair and per IP, never per email alone:
    a per-email limit lets anyone lock a user out by typing wrong passwords
    for their address.
    """
    now = datetime.now()
    cutoff = (now - timedelta(seconds=window_seconds)).isoformat()
    ip_cutoff = (now - timedelta(seconds=ip_window_seconds)).isoformat()
    cur = get_db().cursor()
    cur.execute("SELECT COUNT(*) FROM login_attempts WHERE success = 0 AND timestamp >= ? AND email = ? AND ip = ?",
                (cutoff, email, ip))
    pair_failures = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM login_attempts WHERE success = 0 AND timestamp >= ? AND ip = ?",
                (ip_cutoff, ip))
    ip_failures = cur.fetchone()[0]
    cur.close()
    return pair_failures >= max_attempts or ip_failures >= ip_max_attempts

def record_login_attempt(email: str, ip: str, success: bool):
    db = get_db()
    cur = db.cursor()
    cur.execute("INSERT INTO login_attempts(email, ip, timestamp, success) VALUES (?,?,?,?)",
                (email[:254], ip, datetime.now().isoformat(), 1 if success else 0))
    # Housekeeping: nothing reads attempts older than 30 days.
    cur.execute("DELETE FROM login_attempts WHERE timestamp < ?", ((datetime.now() - timedelta(days=30)).isoformat(),))
    db.commit()
    cur.close()

def hit_rate_limit(action: str, key: str, limit: int, window_seconds: int) -> bool:
    """Count one event for (action, key). Returns True if the limit was already reached.

    Blocked attempts are not counted, so a limit always clears after `window_seconds`.
    """
    now = datetime.now()
    cutoff = (now - timedelta(seconds=window_seconds)).isoformat()
    db = get_db()
    cur = db.cursor()
    cur.execute("SELECT COUNT(*) FROM rate_events WHERE action = ? AND key = ? AND timestamp >= ?",
                (action, key, cutoff))
    if cur.fetchone()[0] >= limit:
        cur.close()
        return True
    cur.execute("INSERT INTO rate_events(action, key, timestamp) VALUES (?,?,?)", (action, key, now.isoformat()))
    # Housekeeping: nothing uses events older than 2 days.
    cur.execute("DELETE FROM rate_events WHERE timestamp < ?", ((now - timedelta(days=2)).isoformat(),))
    db.commit()
    cur.close()
    return False

def is_delete_token_valid(token):
    cur = get_db().cursor()
    cur.execute("SELECT delete_token_expires_at FROM users WHERE delete_token = ?", (token,))
    row = cur.fetchone()
    cur.close()
    return bool(row) and not is_token_expired(row[0])

def handle_delete_confirmation(token):
    if not token:
        return "Invalid token", 400
    
    cur = get_db().cursor()
    cur.execute("SELECT id, email, delete_token_expires_at FROM users WHERE delete_token = ?", (token,))
    user = cur.fetchone()
    
    if not user:
        cur.close()
        return "Invalid or expired token", 400

    user_id, email, expires_at = user
    
    if is_token_expired(expires_at):
        cur.close()
        return "Invalid or expired token", 400 

    try:
        cur.execute("DELETE FROM transactions WHERE user_id = ?", (user_id,))
        cur.execute("DELETE FROM users WHERE id = ?", (user_id,))
        get_db().commit()
        cur.close()
        
        if 'email' in session and session['email'].lower() == email.lower():
            session.pop('email', None)
        
        current_app.logger.info(f"Account deleted successfully for {email}")
        return render_template('delete_account.html', success="Your account has been permanently deleted.")
        
    except Exception as e:
        get_db().rollback()
        cur.close()
        current_app.logger.error(f"Error deleting account for {email}: {e}")
        return "An error occurred while deleting your account", 500
