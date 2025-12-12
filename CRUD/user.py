from flask import request, render_template, redirect, url_for, session
from app import app
from utils.utils import password_validator, email_validator
from tokens import create_token_with_expiry
import os, bcrypt
from dotenv import load_dotenv
from db import get_db
from utils.utils import get_client_ip
from emails import send_delete_account_email, send_reset_password_email, send_verification_email
from utils.utils import is_rate_limited, record_login_attempt, handle_delete_confirmation
from tokens import is_token_expired

load_dotenv()

BCRYPT_ROUNDS = int(os.getenv("BCRYPT_ROUNDS"))

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        email = request.form['email'].lower()
        password = request.form['password']
        confirm_password = request.form.get('confirm_password')
        if not email or not password or not confirm_password:
            error='email and password missing'
            return render_template('signup.html', error=error)
        
        if password != confirm_password:
            error = "Passwords don't match"
            return render_template("signup.html", error=error)

        ok, error = password_validator(password)
        if not ok:
            return render_template("signup.html", error=error)

        if not email_validator(email):
            error = 'Invalid email'
            return render_template('signup.html', error=error)
        
        bytes = password.encode('utf-8')
        salt = bcrypt.gensalt(rounds=BCRYPT_ROUNDS)
        hash = bcrypt.hashpw(bytes, salt)

        verification_token, verification_expires_at = create_token_with_expiry(hours=24)

        is_verified = 0

        cur = get_db().cursor()
        cur.execute("SELECT * FROM users WHERE email = ?", (email,))
        check = cur.fetchone()
        
        if check is None:
            cur.execute("INSERT INTO users(email, password, is_verified, verification_token, verification_token_expires_at) VALUES(?,?,?,?,?)",(email,hash,is_verified,verification_token, verification_expires_at))
            get_db().commit()
            cur.close()

            app.logger.info(f"New user created: {email}")
            send_verification_email(email, verification_token)
            return redirect(url_for('login'))
        else:
            cur.close()
            error='User with this email already exist'
            return render_template('signup.html', error=error)
    return render_template('signup.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        ip = get_client_ip()
        email = request.form['email']
        password = request.form['password']

        if is_rate_limited(email, ip, window_seconds=300, max_attempts=5):
            app.logger.warning(f"Rate limit: too many login attempts for {email} from {ip}")
            return render_template('login.html', error='Too many login attempts. Please try again later.')

        if not email or not password:
            app.logger.warning(f'Failed login attempt - Missing email or password. Email: {email}')
            record_login_attempt(email, ip, success=False)
            return render_template('login.html', error="Invalid email or password")
        
        if not email_validator(email):
            app.logger.warning(f'Failed login attempt - Invalid email format. Email: {email}')
            record_login_attempt(email, ip, success=False)
            return render_template('login.html', error="Invalid email or password")
        
        cur = get_db().cursor()
        cur.execute("SELECT password, is_verified FROM users WHERE email = ?", (email,))
        user = cur.fetchone()
        cur.close()

        if not user:
            app.logger.warning(f'Failed login attempt - User not found or wrong password. Email: {email}')
            record_login_attempt(email, ip, success=False)
            return render_template('login.html', error="Invalid email or password")

        hashed_pw, is_verified = user

        if not bcrypt.checkpw(password.encode('utf-8'), hashed_pw):
            app.logger.warning(f'Failed login attempt - Wrong password. Email: {email}')
            record_login_attempt(email, ip, success=False)
            return render_template('login.html', error="Invalid email or password")

        if is_verified == 0:
            app.logger.warning(f'Failed login attempt - Email not verified. Email: {email}')
            record_login_attempt(email, ip, success=False)
            return render_template('login.html', error="Please verify your email")
        
        session.clear()
        session['email'] = email
        session.permanent = True

        record_login_attempt(email, ip, success=True)

        app.logger.info(f'{email} successfully logged in')
        return redirect(url_for('index'))

    return render_template('login.html')

@app.route('/logout')
def logout():
    email = session['email']
    session.pop('email', None)
    app.logger.info(f'{email} -- logged out')
    return render_template('login.html')


@app.route('/verify')
def verify():
    token = request.args.get('token')

    if not token:
        return {"error:":"Invalid verification link."}, 400

    cur = get_db().cursor()
    cur.execute("SELECT id, is_verified, verification_token_expires_at FROM users WHERE verification_token = ?", (token,))
    user = cur.fetchone()

    if user:
        user_id, is_verified, expires_at = user

        if is_token_expired(expires_at):
            cur.close()
            return {"error": "Verification link has expired."}, 400
        
        if is_verified:
            message = "Email already verified."
        else:
            cur.execute("UPDATE users SET is_verified = 1, verification_token = NULL, verification_token_expires_at = NULL WHERE id = ?", (user_id,))
            get_db().commit()
            message = "Email verified successfully!"
        cur.close()
        return render_template("verification_email.html", message=message)
    else:
        cur.close()
        return {"error":"Invalid or expired verification token."}, 404

@app.route('/change_password', methods=['GET', 'POST'])
def change_password():
    if 'email' not in session:
        return redirect(url_for('login'))

    email = session['email']
    db = get_db()
    cur = db.cursor()
    cur.execute("SELECT password FROM users WHERE email = ?", (email,))
    user = cur.fetchone()
    if not user:
        return redirect(url_for('login'))

    if request.method == 'POST':
        current_password = request.form['current_password']
        new_password = request.form['new_password']
        confirm_password = request.form['confirm_password']

        if not bcrypt.checkpw(current_password.encode('utf-8'), user[0]):
            return render_template('change_password.html', error="Current password is incorrect")

        if new_password != confirm_password:
            return render_template('change_password.html', error="New passwords do not match")

        ok, error = password_validator(new_password)
        if not ok:
            return render_template("change_password.html", error=error)

        new_hash = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt())
        cur.execute("UPDATE users SET password = ? WHERE email = ?", (new_hash, email))
        db.commit()
        cur.close()

        app.logger.info(f"{email} -- changed password")
        return render_template('change_password.html', success="Password changed successfully")
    return render_template('change_password.html')

@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if "email" in session:
        return redirect(url_for("index"))

    if request.method == 'POST':
        ip = get_client_ip()
        email = request.form['email'].lower()

        if is_rate_limited(email, ip, window_seconds=900, max_attempts=5):
            app.logger.warning(f"Rate limit: too many password reset attempts for {email} from {ip}")
            return render_template("forgot_password.html", msg="Too many attempts to reset your password, please try later")

        if not email or not email_validator(email):
            record_login_attempt(email, ip, success=False)
            return render_template('forgot_password.html', msg="If an account with this email exists, a password reset link has been sent.")

        cur = get_db().cursor()
        cur.execute("SELECT id FROM users WHERE email = ?", (email,))
        user = cur.fetchone()
        if not user:
            cur.close()
            record_login_attempt(email, ip, False)
            return render_template('forgot_password.html', msg="If an account with this email exists, a password reset link has been sent.")

        reset_token, reset_expires_at = create_token_with_expiry(hours=1)
        cur.execute("UPDATE users SET reset_token = ?, reset_token_expires_at = ? WHERE email = ?", (reset_token, reset_expires_at,email))
        get_db().commit()
        cur.close()
        send_reset_password_email(email, reset_token)
        record_login_attempt(email, ip, True)
        return render_template('forgot_password.html', msg="If an account with this email exists, a password reset link has been sent.")
    return render_template('forgot_password.html')

@app.route('/reset_password', methods=['GET', 'POST'])
def reset_password():
    token = request.args.get('token') or request.form.get('token')
    if not token:
        return "Invalid or missing token", 400

    if request.method == 'POST':
        new_password = request.form['new_password']
        confirm_password = request.form['confirm_password']
        if new_password != confirm_password:
            return render_template('reset_password.html', token=token, error="Passwords do not match")

        ok, error = password_validator(new_password)
        if not ok:
            return render_template("reset_password.html", token=token, error=error)

        cur = get_db().cursor()
        cur.execute("SELECT email, reset_token_expires_at FROM users WHERE reset_token = ?", (token,))
        user = cur.fetchone()
        if not user:
            cur.close()
            return "Invalid or expired token", 400
        
        email, expires_at = user

        if is_token_expired(expires_at):
            cur.close()
            return "Invalid or expired token", 400

        new_hash = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt())
        cur.execute("UPDATE users SET password = ?, reset_token = NULL, reset_token_expires_at = NULL WHERE reset_token = ?", (new_hash, token))
        get_db().commit()
        cur.close()
        return render_template('reset_password.html', success="Password changed successfully")
    return render_template('reset_password.html', token=token)

@app.route("/delete_account", methods=['GET', 'POST'])
def delete_account():
    token = request.args.get('token')
    if token:
        return handle_delete_confirmation(token)
    
    if 'email' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        email = request.form.get('email', '').lower()
        session_email = session['email'].lower()
        
        if email != session_email:
            return render_template('delete_account.html', error="Email doesn't match your account")
        
        if not email_validator(email):
            return render_template('delete_account.html', error="Invalid email format")
        
        delete_token, delete_expires_at = create_token_with_expiry(hours=1)
        
        cur = get_db().cursor()
        cur.execute("UPDATE users SET delete_token = ?, delete_token_expires_at = ? WHERE email = ?", (delete_token, delete_expires_at, email))
        get_db().commit()
        cur.close()
        
        send_delete_account_email(email, delete_token)
        app.logger.info(f"Delete account request initiated for {email}")
        
        return render_template('delete_account.html', success="Confirmation email sent. Please check your inbox.")
    
    return render_template('delete_account.html')