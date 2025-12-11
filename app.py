from flask import Flask, render_template, session, request, redirect, url_for, g, jsonify, make_response
from flask_wtf.csrf import CSRFProtect
from dotenv import load_dotenv
import os, sqlite3, bcrypt
from datetime import datetime, timedelta
from calendar import monthrange
from email_validator import validate_email,EmailNotValidError
import secrets
import sib_api_v3_sdk
from sib_api_v3_sdk.rest import ApiException
import logging
from logging.handlers import RotatingFileHandler
from werkzeug.middleware.proxy_fix import ProxyFix

load_dotenv()

class BaseConfig:
    SECRET_KEY = os.getenv("SECRET_KEY")
    DATABASE = os.getenv("DATABASE")
    WTF_CSRF_TIME_LIMIT = 3600
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    PERMANENT_SESSION_LIFETIME = 60 * 60 * 8
    TEMPLATES_AUTO_RELOAD = False
    DEBUG = False

class DevelopmentConfig(BaseConfig):
    DEBUG = True
    TEMPLATES_AUTO_RELOAD = True
    SESSION_COOKIE_SECURE = False
    PREFERRED_URL_SCHEME = "http"
    BASE_URL = "http://127.0.0.1:5000"

class ProductionConfig(BaseConfig):
    SESSION_COOKIE_SECURE = True
    PREFERRED_URL_SCHEME = "https"
    BASE_URL = "https://ledger.vsteschenko.me"


app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

env = os.getenv("FLASK_ENV", "production").lower()
BCRYPT_ROUNDS = int(os.getenv("BCRYPT_ROUNDS"))

if env == "development":
    app.config.from_object(DevelopmentConfig)
else:
    app.config.from_object(ProductionConfig)

csrf = CSRFProtect(app)

log_file = 'app.log'
handler = RotatingFileHandler(log_file, maxBytes=10000000, backupCount=3)
handler.setLevel(logging.INFO)

formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
app.logger.addHandler(handler)

console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)
console_handler.setFormatter(formatter)
app.logger.addHandler(console_handler)
app.logger.setLevel(logging.INFO)

category_name = {
    "beauty": "Beauty & Personal Care",
    "education": "Childcare & Education",
    "credit_card": "Credit Card Payments",
    "dining": "Dining Out",
    "entertainment": "Entertainment",
    "gifts": "Gifts & Donations",
    "grocery": "Grocery",
    "health": "Health & Fitness",
    "home_maintenance": "Home Maintenance",
    "insurance": "Insurance",
    "loans": "Loan Payments",
    "pets": "Pets",
    "rent": "Rent",
    "savings": "Savings & Investments",
    "shopping": "Shopping",
    "subscriptions": "Subscriptions & Memberships",
    "transport": "Transportation",
    "travel": "Travel",
    "utilities": "Utilities",
    "work": "Work",
    "other": "Other"
}

@app.after_request
def add_security_headers(response):
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains; preload'
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = ("geolocation=(), microphone=(), camera=(), payment=(), usb=(), fullscreen=(self)")
    response.headers["Cross-Origin-Opener-Policy"] = "same-origin"
    response.headers["Cross-Origin-Resource-Policy"] = "same-origin"
    csp = (
        "default-src 'self'; "
        "script-src 'self' https://cdn.jsdelivr.net 'unsafe-inline'; "
        "style-src 'self' https://cdn.jsdelivr.net 'unsafe-inline'; "
        "img-src 'self' data:; "
        "font-src 'self' https://cdn.jsdelivr.net data:; "
        "connect-src 'self'; "
        "frame-ancestors 'none'; "
        "base-uri 'self'; "
        "form-action 'self'"
    )
    response.headers["Content-Security-Policy"] = csp
    return response

@app.template_filter('datetimeformat')
def datetimeformat(value, format='%H:%M'):
    dt = datetime.strptime(value, '%Y-%m-%d %H:%M:%S')
    return dt.strftime(format)

@app.template_filter('currency')
def currency_format(value):
    if value is None:
        return "0.00"
    return "{:.2f}".format(float(value))

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(app.config["DATABASE"])
    return db

def get_client_ip():
    return request.headers.get("X-Forwarded-For", request.remote_addr or "unknown")

def record_login_attempt(email: str, ip: str, success: bool):
    db = get_db()
    cur = db.cursor()
    if not email_validator(email):
        return "Incorrect email"
    cur.execute("INSERT INTO login_attempts(email, ip, timestamp, success) VALUES (?,?,?,?)", (email, ip, datetime.now().isoformat(), 1 if success else 0))
    db.commit()
    db.close()

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

configuration = sib_api_v3_sdk.Configuration()
configuration.api_key['api-key'] = os.getenv("BREVO_API_KEY")

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

def send_verification_email(email, token):
    base_url = app.config["BASE_URL"]
    new_url = f"{base_url}/verify?token={token}"
    api_instance = sib_api_v3_sdk.TransactionalEmailsApi(sib_api_v3_sdk.ApiClient(configuration))
    subject = "Verify your email"
    sender = {"name": "Ledger", "email": "slava@vsteschenko.me"}
    to = [{"email": email}]   
    html_content = f"""
    <html>
      <body>
        <p>Hi!</p>
        <p>Verify your email by clicking the link below:</p>
        <a href={new_url}>Verify Email</a>
      </body>
    </html>
    """

    send_smtp_email = sib_api_v3_sdk.SendSmtpEmail(
        to=to,
        sender=sender,
        subject=subject,
        html_content=html_content,
    )

    try:
        response = api_instance.send_transac_email(send_smtp_email)
        app.logger.info(f"Verification email sent to {email}. Message ID: {response.message_id}")
    except ApiException as e:
        app.logger.error(f"Failed to send verification email: {e}")

def generate_token():
    return secrets.token_urlsafe(32)

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def get_user_id(email):
    cur = get_db().cursor()
    cur.execute("SELECT id FROM users WHERE email = ?", (email,))
    row = cur.fetchone()
    cur.close()
    return row[0] if row else None

@app.route('/', methods=['GET', 'POST'])
def index():
    if 'email' in session:
        email = session["email"]
        user_id = get_user_id(email)

        current_year = datetime.now().year
        current_month = datetime.now().month
        current_day = datetime.now().day
        username = email.split("@")[0]
        if 'year' in request.args:
            current_year = int(request.args.get('year'))

        if 'month' in request.args:
            current_month = int(request.args.get('month'))
            if current_month < 1:
                current_month = 12
                current_year -= 1
            elif current_month > 12:
                current_month = 1
                current_year += 1
        
        if 'day' in request.args:
            current_day = int(request.args.get('day'))
            days_in_month = monthrange(current_year, current_month)[1]
            if current_day < 1:
                current_month -= 1
                if current_month < 1:
                    current_month = 12
                    current_year -= 1
                current_day = monthrange(current_year, current_month)[1]
            elif current_day > days_in_month:
                current_month += 1
                if current_month > 12:
                    current_month = 1
                    current_year += 1
                current_day = 1

        start_of_day = datetime(current_year, current_month, current_day, 0, 0, 0).strftime('%Y-%m-%d %H:%M:%S')
        end_of_day = datetime(current_year, current_month, current_day, 23, 59, 59).strftime('%Y-%m-%d %H:%M:%S')

        cur = get_db().cursor()
        cur.execute("""
            SELECT transactions.amount, transactions.type, transactions.id, transactions.timestamp, transactions.category, transactions.place
            FROM transactions JOIN users ON transactions.user_id=users.id 
            WHERE users.id = ? AND transactions.timestamp BETWEEN ? AND ?
            """, (user_id, start_of_day, end_of_day))
        transactions = cur.fetchall()

        transactions.sort(key=lambda tx: datetime.strptime(tx[3], "%Y-%m-%d %H:%M:%S"))

        cur.execute("""
            SELECT category, SUM(amount)
            FROM transactions
            JOIN users ON transactions.user_id=users.id
            WHERE user_id=? AND type='expense' AND timestamp BETWEEN ? AND ?
            GROUP BY category
            """, (user_id, start_of_day, end_of_day))
        sum_by_categories = cur.fetchall()
 
        cur.execute("""
            SELECT SUM(amount) 
            FROM transactions 
            WHERE user_id=? AND timestamp BETWEEN ? AND ?
            """, (user_id, start_of_day, end_of_day))
        sum = cur.fetchone()[0]

        if request.method == 'POST':
            type = request.form['type']
            place = request.form['place']
            time = request.form['tx_time']
            hour, minute = map(int, time.split(':'))
            transaction_date = datetime(current_year, current_month, current_day, hour, minute)
            if len(place) > 100:
                return {'error': 'Name of the place is too long'}, 404

            if type == 'expense':
                category = request.form.get('expense-category')
            elif type == 'income':
                category = request.form.get('income-category')

            amount = request.form['amount']
            if type == 'expense':
                amount = -float(amount)

            if not type or not amount or not user_id or not category or not transaction_date:
                return {'error': 'Select category'}, 401
            cur.execute("INSERT INTO transactions(type,amount,user_id,timestamp,category,place) VALUES(?,?,?,?,?,?)",(type, amount, user_id, transaction_date, category, place))
            get_db().commit()
            cur.close()

            app.logger.info(f'{email} -- Added transaction')

            return redirect(url_for("index", month=current_month, day=current_day, year=current_year, username=username))
        return render_template("index.html", txs=transactions, sum=sum or 0, current_month=current_month, current_day=current_day, current_year=current_year, sum_by_categories=sum_by_categories, username=username)
    else:
        return redirect(url_for('login'))

@app.route('/expenses_by_category')
def expenses_by_category():
    if 'email' not in session:
        return {"error": "Not logged in"}, 401

    email = session["email"]
    user_id = get_user_id(email)

    current_year = int(request.args.get('year'))
    current_month = int(request.args.get('month'))
    current_day = int(request.args.get('day'))

    start_of_day = datetime(current_year, current_month, current_day).strftime('%Y-%m-%d %H:%M:%S')
    end_of_day = datetime(current_year, current_month, current_day, 23, 59, 59).strftime('%Y-%m-%d %H:%M:%S')

    cur = get_db().cursor()
    cur.execute("""
        SELECT category, SUM(amount)
        FROM transactions
        WHERE user_id=? AND type='expense' AND timestamp BETWEEN ? AND ?
        GROUP BY category
        """, (
            user_id,
            start_of_day,
            end_of_day
        ))
    data = cur.fetchall()
    cur.close()
    categories = [row[0] for row in data]
    amounts = [round(abs(float(row[1])), 2) for row in data]
    real_amounts = amounts
    total = sum(amounts)
    if total > 0:
        amounts = [round(amount * 100 / total, 1) for amount in amounts]
    else:
        amounts = [0 for _ in amounts]
    return jsonify({"categories": categories, "amounts": amounts, "real_amounts": real_amounts})

@app.route('/report', methods=['GET', 'POST'])
def report():
    if 'email' in session:
        year = request.args.get('year', type=int, default=datetime.now().year)
        month = request.args.get('month', type=int, default=datetime.now().month)
        email = session["email"]
        username = email.split("@")[0]
        user_id = get_user_id(email)
        timestamp_pattern = f"{year:04d}-{month:02d}-%"

        cur = get_db().cursor()
        cur.execute("SELECT SUM(amount) FROM transactions WHERE user_id=? AND type='expense' AND timestamp LIKE ?", (user_id, timestamp_pattern))
        expenses = cur.fetchone()[0]
        cur.execute("SELECT SUM(amount) FROM transactions WHERE user_id=? AND type='income' AND timestamp LIKE ?", (user_id, timestamp_pattern))
        income = cur.fetchone()[0]
        get_db().commit()
        cur.close()
        if expenses == None:
            expenses = 0
        if income == None:
            income = 0
        
        expenses = round(float(expenses), 2)
        income = round(float(income), 2)
        
        return render_template('report.html', current_year=year, current_month=month, expenses=expenses, income=income, username=username)
    return redirect(url_for('login'))

@app.route('/annual_report', methods=["GET", "POST"])
def annual_report():
    if "email" not in session:
        return redirect(url_for('login'))
    year = request.args.get('year', type=int, default=datetime.now().year)
    month = request.args.get('month', type=int, default=datetime.now().month)
    email = session["email"]
    username = email.split("@")[0]
    user_id = get_user_id(email)
    timestamp_pattern = f"{year}%"

    cur = get_db().cursor()
    cur.execute("SELECT SUM(amount) FROM transactions WHERE user_id=? AND type='expense' AND timestamp LIKE ?", (user_id, timestamp_pattern))
    expense = cur.fetchone()[0]
    if expense is None:
        expense = 0
    cur.execute("SELECT SUM(amount) FROM transactions WHERE user_id=? AND type='income' AND timestamp LIKE ?", (user_id, timestamp_pattern))
    income = cur.fetchone()[0]
    if income is None:
        income = 0
    cur.execute("SELECT category, SUM(amount) FROM transactions WHERE user_id=? AND type='expense' AND timestamp LIKE ? GROUP BY category", (user_id, timestamp_pattern))
    sum_by_category = cur.fetchall()
    new_sum_by_category = []
    for cat in sum_by_category:
        x = category_name[cat[0]]
        new_tx = (cat[0], cat[1], x)
        new_sum_by_category.append(new_tx)
    sum_by_category = new_sum_by_category
    return render_template('annual_report.html', current_year=year, current_month=month, username=username, expense=expense, income=income, sum_by_category=sum_by_category)

@app.route('/report_chart', methods=['GET'])
def report_chart():
    if 'email' in session:
        year = request.args.get('year', type=int, default=datetime.now().year)
        month = request.args.get('month', type=int, default=datetime.now().month)
        email = session["email"]
        user_id = get_user_id(email)
        timestamp_pattern = f"{year:04d}-{month:02d}-%"

        cur = get_db().cursor()
        cur.execute("SELECT category, SUM(amount) FROM transactions WHERE user_id=? AND type='expense' AND timestamp LIKE ? GROUP BY category ", (user_id, timestamp_pattern))
        data = cur.fetchall()
        get_db().commit()
        cur.close()

        categories = [row[0] for row in data]
        amounts = [round(float(row[1]) * -1, 2) for row in data]

        return jsonify({"categories": categories,"amounts": amounts})
    return jsonify({"error": "Unauthorized"}), 401

@app.route('/delete_tx', methods=['POST'])
def delete_tx():
    if 'email' in session:
        email = session["email"]
        tx_id = request.form['tx_id']
        user_id = get_user_id(email)
        if user_id is None:
            app.logger.warning(f"User with email {email} not found.")
            return redirect(url_for('login'))
        
        cur = get_db().cursor()
        cur.execute("DELETE FROM transactions WHERE id = ? AND user_id = ?", (tx_id, user_id))
        get_db().commit()
        if cur.rowcount == 0:
            app.logger.warning(f"{email} -- tried to delete transaction {tx_id}, but it doesn't exist.")
        else:
            app.logger.info(f"{email} -- deleted transaction {tx_id}")
        cur.close()
        app.logger.info(f'{email} -- deleted transaction {tx_id}')

        current_year = request.form.get('year')
        current_month = request.form.get('month')
        current_day = request.form.get('day')
        return redirect(url_for('index', year=current_year, month=current_month, day=current_day))
    return redirect(url_for('login'))

@app.route('/update_tx', methods=['POST'])
def update_tx():
    if 'email' in session:
        email = session['email']
        user_id = get_user_id(email)
        tx_id = request.form['tx_id']
        type = request.form['type']
        place = request.form['place']
        amount = request.form['amount']
        current_year = int(request.form.get('year'))
        current_month = int(request.form.get('month'))
        current_day = int(request.form.get('day'))
        time = request.form['tx_time']
        hour, minute = map(int, time.split(':'))
        transaction_date = datetime(current_year, current_month, current_day, hour, minute)

        if type == 'expense':
            category = request.form.get('expense-category')
            amount = -float(amount)
        elif type == 'income':
            category = request.form.get('income-category')
            amount = float(amount)

        if not tx_id or not type or not place or not amount or not category or not transaction_date:
            return {'error': 'All fields are required'}, 400
        if len(place) > 100:
            return {'error': 'Place name is too long'}, 400
        try:
            amount = float(amount)
        except ValueError:
            return {'error': 'Invalid amount'}, 400

        cur = get_db().cursor()

        cur.execute("SELECT id FROM transactions WHERE id = ? AND user_id = ?", (tx_id, user_id))
        if not cur.fetchone():
            return {'error': 'Transaction not found or access denied'}, 404

        cur.execute("""
            UPDATE transactions
            SET type = ?, place = ?, amount = ?, category = ?, timestamp = ?
            WHERE id = ? AND user_id = ?
        """, (type, place, amount, category, transaction_date, tx_id, user_id))
        get_db().commit()
        cur.close()

        app.logger.info(f'{email} -- updated transaction {tx_id}')

        return redirect(url_for('index', year=current_year, month=current_month, day=current_day))
    return redirect(url_for('login'))

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

def send_reset_password_email(email, token):
    base_url = app.config["BASE_URL"]
    new_url = f"{base_url}/reset_password?token={token}"
    api_instance = sib_api_v3_sdk.TransactionalEmailsApi(sib_api_v3_sdk.ApiClient(configuration))
    subject = "Password Reset Request"
    sender = {"name": "Slava", "email": "slava@vsteschenko.me"}
    to = [{"email": email}]
    html_content = f"""
    <html>
      <body>
        <p>Hi!</p>
        <p>To reset your password, click the link below:</p>
        <a href={new_url}>Reset Password</a>
      </body>
    </html>
    """

    send_smtp_email = sib_api_v3_sdk.SendSmtpEmail(
        to=to,
        sender=sender,
        subject=subject,
        html_content=html_content,
    )

    try:
        response = api_instance.send_transac_email(send_smtp_email)
        app.logger.info(f"Password reset email sent to {email}. Message ID: {response.message_id}")
    except ApiException as e:
        app.logger.error(f"Failed to send password reset email: {e}")

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

@app.route("/ledger", methods=['GET'])
def ledger():
    return render_template('ledger.html')

@app.route("/transactions_by_categories", methods=['GET'])
def transactions_by_categories():
    if "email" not in session:
        return redirect(url_for("index"))
    email = session['email']
    user_id = get_user_id(email)
    category = request.args.get("category")
    year = int(request.args.get("year", datetime.now().year))
    month = int(request.args.get("month", datetime.now().month))

    if not category:
        return jsonify({"error": "category is required"}), 400

    first_day = datetime(year, month, 1, 0, 0, 0)
    last_day_num = monthrange(year, month)[1]
    last_day = datetime(year, month, last_day_num, 23, 59, 59)

    cur = get_db().cursor()
    cur.execute("SELECT amount, timestamp, category, place FROM transactions WHERE user_id=? AND type='expense' AND category=? AND timestamp BETWEEN ? AND ? ORDER BY timestamp ASC", (user_id, category, first_day, last_day))
    rows = cur.fetchall()
    cur.close()

    transactions = [
        {
            "amount": float(amount),
            "timestamp": timestamp,
            "category": category,
            "place": place,
        }
        for amount, timestamp, category, place in rows
    ]
    return jsonify(transactions)

@app.route("/transactions_by_categories_year", methods=['GET'])
def transactions_by_categories_year():
    if "email" not in session:
        return redirect(url_for("index"))
    email = session['email']
    user_id = get_user_id(email)
    category = request.args.get("category")
    year = int(request.args.get("year", datetime.now().year))
    if not category:
        return jsonify({"error": "category is required"}), 400

    start_of_year = datetime(year, 1, 1, 0, 0, 0)
    end_of_year = datetime(year, 12, 31, 23, 59, 59)

    cur = get_db().cursor()
    cur.execute(
        """
        SELECT amount, timestamp, category, place
        FROM transactions
        WHERE user_id=?
          AND type='expense'
          AND category=?
          AND timestamp BETWEEN ? AND ?
        ORDER BY timestamp ASC
        """,
        (user_id, category, start_of_year, end_of_year),
    )
    rows = cur.fetchall()
    cur.close()

    transactions = [
        {
            "amount": float(amount),
            "timestamp": timestamp,
            "category": category,
            "place": place,
        }
        for amount, timestamp, category, place in rows
    ]
    return jsonify(transactions)

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
        
        app.logger.info(f"Account deleted successfully for {email}")
        return render_template('delete_account.html', success="Your account has been permanently deleted.")
        
    except Exception as e:
        get_db().rollback()
        cur.close()
        app.logger.error(f"Error deleting account for {email}: {e}")
        return "An error occurred while deleting your account", 500

def send_delete_account_email(email, token):
    base_url = app.config["BASE_URL"]
    new_url = f"{base_url}/delete_account?token={token}"
    api_instance = sib_api_v3_sdk.TransactionalEmailsApi(sib_api_v3_sdk.ApiClient(configuration))
    subject = "Ledger Delete Account Request"
    sender = {"name": "Slava", "email": "slava@vsteschenko.me"}
    to = [{"email": email}]
    html_content = f"""
    <html>
      <body>
        <p>Hi!</p>
        <p>You have requested to delete your account. This action is irreversible and will permanently remove all your data.</p>
        <p>To confirm account deletion, click the link below:</p>
        <a href={new_url}>Delete account</a>
      </body>
    </html>
    """

    send_smtp_email = sib_api_v3_sdk.SendSmtpEmail(
        to=to,
        sender=sender,
        subject=subject,
        html_content=html_content,
    )

    try:
        response = api_instance.send_transac_email(send_smtp_email)
        app.logger.info(f"Delete Account email sent to {email}. Message ID: {response.message_id}")
    except ApiException as e:
        app.logger.error(f"Failed to send delete account email: {e}")
