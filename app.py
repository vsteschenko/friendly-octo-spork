from flask import Flask, render_template, session, request, redirect, url_for, g, jsonify, make_response
from dotenv import load_dotenv
import os, sqlite3, bcrypt
from datetime import datetime
from calendar import monthrange
from email_validator import validate_email,EmailNotValidError
import secrets
import sib_api_v3_sdk
from sib_api_v3_sdk.rest import ApiException
import logging
from logging.handlers import RotatingFileHandler

load_dotenv()

app = Flask(__name__)
app.config["DATABASE"] = os.getenv("DATABASE")
app.secret_key = os.getenv("SECRET_KEY")

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

def email_validator(email):
    try:
        validate_email(email)
        return True
    except EmailNotValidError:
        return False

configuration = sib_api_v3_sdk.Configuration()
configuration.api_key['api-key'] = os.getenv("BREVO_API_KEY")

# <a href="http://127.0.0.1:5000/verify?token={token}">Verify Email</a>
# <a href="https://ledger.vsteschenko.me/verify?token={token}">Verify Email</a>
def send_verification_email(email, token):
    api_instance = sib_api_v3_sdk.TransactionalEmailsApi(sib_api_v3_sdk.ApiClient(configuration))
    subject = "Verify your email"
    sender = {"name": "Ledger", "email": "slava@vsteschenko.me"}
    to = [{"email": email}]
    html_content = f"""
    <html>
      <body>
        <p>Hi!</p>
        <p>Verify your email by clicking the link below:</p>
        <a href="https://ledger.vsteschenko.me/verify?token={token}">Verify Email</a>
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
        # ЗДЕСЬ ПОМЕНЯТЬ НАЗВАНИЯ КАТЕГОРИЙ
        # categories = [category_name[category] for category in categories] ПРИМЕРНО ТАК
 
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

    # categories = [category_name[category] for category in categories]

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

        if not email_validator(email):
            error = 'Invalid email'
            return render_template('signup.html', error=error)
        
        bytes = password.encode('utf-8')
        salt = bcrypt.gensalt()
        hash = bcrypt.hashpw(bytes, salt)

        verification_token = generate_token()

        is_verified = 0

        cur = get_db().cursor()
        cur.execute("SELECT * FROM users WHERE email = ?", (email,))
        check = cur.fetchone()
        
        if check is None:
            cur.execute("INSERT INTO users(email, password, is_verified, verification_token) VALUES(?,?,?,?)",(email,hash,is_verified,verification_token))
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
        email = request.form['email']
        password = request.form['password']

        if not email or not password:
            app.logger.warning(f'Failed login attempt - Missing email or password. Email: {email}')
            return render_template('login.html')
        
        if not email_validator(email):
            error = 'Invalid email'
            app.logger.warning(f'Failed login attempt - Invalid email format. Email: {email}')
            return render_template('signup.html', error=error)
        
        cur = get_db().cursor()
        cur.execute("SELECT password, is_verified FROM users WHERE email = ?", (email,))
        user = cur.fetchone()
        cur.close()

        if not user:
            error = "User with this email doesn't exist"
            app.logger.warning(f'Failed login attempt - User not found. Email: {email}')
            return render_template('login.html', error=error)

        if bcrypt.checkpw(password.encode('utf-8'), user[0]):
            if user[1] == 0:
                error = 'Please verify your email'
                app.logger.warning(f'Failed login attempt - Email not verified. Email: {email}')
                return render_template('login.html', error=error)
            session['email'] = email
            app.logger.info(f'{email} successfully logged in')
            return redirect(url_for('index'))
        else:
            error = 'Invalid email or password'
            app.logger.warning(f'Failed login attempt - Incorrect password. Email: {email}')
            return render_template('login.html', error=error)
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
    cur.execute("SELECT id, is_verified FROM users WHERE verification_token = ?", (token,))
    user = cur.fetchone()

    if user:
        user_id, is_verified = user
        if is_verified:
            message = "Email already verified."
        else:
            cur.execute("UPDATE users SET is_verified = 1, verification_token = NULL WHERE id = ?", (user_id,))
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

        if len(new_password) < 6:
            return render_template('change_password.html', error="Password must be at least 6 characters")

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
        email = request.form['email'].lower()
        if not email or not email_validator(email):
            return render_template('forgot_password.html', error="Enter a valid email")

        cur = get_db().cursor()
        cur.execute("SELECT id FROM users WHERE email = ?", (email,))
        user = cur.fetchone()
        if not user:
            cur.close()
            return render_template('forgot_password.html', error="No user with this email")

        reset_token = generate_token()
        cur.execute("UPDATE users SET reset_token = ? WHERE email = ?", (reset_token, email))
        get_db().commit()
        cur.close()
        send_reset_password_email(email, reset_token)
        return render_template('forgot_password.html', success="Password reset link sent to your email")
    return render_template('forgot_password.html')

# <a href="http://127.0.0.1:5000/reset_password?token={token}">Reset Password</a>
# <a href="https://ledger.vsteschenko.me/reset_password?token={token}">Reset Password</a>

def send_reset_password_email(email, token):
    api_instance = sib_api_v3_sdk.TransactionalEmailsApi(sib_api_v3_sdk.ApiClient(configuration))
    subject = "Password Reset Request"
    sender = {"name": "Slava", "email": "slava@vsteschenko.me"}
    to = [{"email": email}]
    html_content = f"""
    <html>
      <body>
        <p>Hi!</p>
        <p>To reset your password, click the link below:</p>
        <a href="https://ledger.vsteschenko.me/reset_password?token={token}">Reset Password</a>
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
        if len(new_password) < 6:
            return render_template('reset_password.html', token=token, error="Password must be at least 6 characters")

        cur = get_db().cursor()
        cur.execute("SELECT email FROM users WHERE reset_token = ?", (token,))
        user = cur.fetchone()
        if not user:
            cur.close()
            return "Invalid or expired token", 400

        new_hash = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt())
        cur.execute("UPDATE users SET password = ?, reset_token = NULL WHERE reset_token = ?", (new_hash, token))
        get_db().commit()
        cur.close()
        return render_template('reset_password.html', success="Password changed successfully")
    return render_template('reset_password.html', token=token)

@app.route("/ledger", methods=['GET'])
def ledger():
    return render_template('ledger.html')

@app.route("/delete_account", methods=['GET', 'POST'])
def delete_account():
    if 'email' not in session:
        return redirect(url_for('login'))
    
    token = request.args.get('token')
    if token:
        return handle_delete_confirmation(token)
    
    if request.method == 'POST':
        email = request.form.get('email', '').lower()
        session_email = session['email'].lower()
        
        if email != session_email:
            return render_template('delete_account.html', error="Email doesn't match your account")
        
        if not email_validator(email):
            return render_template('delete_account.html', error="Invalid email format")
        
        delete_token = generate_token()
        
        cur = get_db().cursor()
        cur.execute("UPDATE users SET delete_token = ? WHERE email = ?", (delete_token, email))
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
    cur.execute("SELECT id, email FROM users WHERE delete_token = ?", (token,))
    user = cur.fetchone()
    
    if not user:
        cur.close()
        return "Invalid or expired token", 400
    
    user_id, email = user
    
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

# <a href="http://127.0.0.1:5000/reset_password?token={token}">Reset Password</a>
# <a href="https://ledger.vsteschenko.me/reset_password?token={token}">Reset Password</a>

def send_delete_account_email(email, token):
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
        <a href="https://ledger.vsteschenko.me/reset_password?token={token}">Reset Password</a>
        <p>If you did not request this, please ignore this email.</p>
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