from email_validator import validate_email,EmailNotValidError
from flask import request, session, render_template, current_app
from db import get_db
from tokens import is_token_expired
from datetime import datetime, timedelta

def email_validator(email):
    try:
        validate_email(email)
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
    return request.headers.get("X-Forwarded-For", request.remote_addr or "unknown")

def get_user_id(email):
    cur = get_db().cursor()
    cur.execute("SELECT id FROM users WHERE email = ?", (email,))
    row = cur.fetchone()
    cur.close()
    return row[0] if row else None

def is_rate_limited(email: str, ip: str, window_seconds: int = 300, max_attempts: int = 5) -> bool:
    cutoff = (datetime.now() - timedelta(seconds=window_seconds)).isoformat()
    db = get_db()
    cur = db.cursor()
    if not email_validator(email):
        return "Incorrect email"
    cur.execute("SELECT COUNT(*) FROM login_attempts WHERE success = 0 AND timestamp >= ? AND (email = ? OR ip = ?)", (cutoff, email, ip))
    count = cur.fetchone()[0]
    cur.close()
    return count >= max_attempts

def record_login_attempt(email: str, ip: str, success: bool):
    db = get_db()
    cur = db.cursor()
    if not email_validator(email):
        return "Incorrect email"
    cur.execute("INSERT INTO login_attempts(email, ip, timestamp, success) VALUES (?,?,?,?)", (email, ip, datetime.now().isoformat(), 1 if success else 0))
    db.commit()
    db.close()

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
