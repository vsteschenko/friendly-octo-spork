from flask import Flask, render_template, session, request, redirect, url_for, g, jsonify
from dotenv import load_dotenv
import os, sqlite3, bcrypt
from datetime import datetime
from calendar import monthrange
from email_validator import validate_email,EmailNotValidError
import secrets
import smtplib
from email.message import EmailMessage
import logging
from logging.handlers import RotatingFileHandler

load_dotenv()
DATABASE = os.getenv("DATABASE")

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY")

# Set up logging to file
log_file = 'app.log'
handler = RotatingFileHandler(log_file, maxBytes=10000000, backupCount=3)
handler.setLevel(logging.INFO)

formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)

app.logger.addHandler(handler)

# Optionally, you can also log to the console for development purposes
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)
console_handler.setFormatter(formatter)
app.logger.addHandler(console_handler)

# Set default logging level
app.logger.setLevel(logging.INFO)

@app.template_filter('datetimeformat')
def datetimeformat(value, format='%H:%M'):
    dt = datetime.strptime(value, '%Y-%m-%d %H:%M:%S')
    return dt.strftime(format)

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
    return db

def email_validator(email):
    try:
        validate_email(email)
        return True
    except EmailNotValidError:
        return False

def send_verification_email(email, token):
    msg = EmailMessage()
    msg['Subject'] = 'Verify you email'
    msg['From'] = 'slava@vsteschenko.me'
    msg['To'] = email
    # msg.set_content(f"Hi! Verify your email here: http://127.0.0.1:5000/verify?token={token}")
    msg.set_content(f"Hi! Verify your email here: https://ledger.vsteschenko.me/verify?token={token}")

    with smtplib.SMTP('smtp-relay.brevo.com', 587) as server:
        server.starttls()
        server.login('8ab566001@smtp-brevo.com', os.getenv("SMTP_PASSWORD"))
        server.send_message(msg)

def generate_token():
    return secrets.token_urlsafe(32)

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def get_user_id(email):
    cur = get_db().cursor()
    cur.execute("SELECT id FROM users WHERE email = ?",(email,))
    user_id = cur.fetchone()
    return user_id

@app.route('/', methods=['GET', 'POST'])
def index():
    if 'email' in session:
        email = session["email"]
        user_id = get_user_id(email)[0]

        current_year = datetime.now().year
        current_month = datetime.now().month
        current_day = datetime.now().day

        # check parameters
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
            SELECT transactions.amount, transactions.type, transactions.id, transactions.timestamp, transactions.category 
            FROM transactions JOIN users ON transactions.user_id=users.id 
            WHERE users.id = ? AND transactions.timestamp BETWEEN ? AND ?
            """, (user_id, start_of_day, end_of_day))
        transactions = cur.fetchall()

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

            # get category
            if type == 'expense':
                category = request.form.get('expense-category')
            elif type == 'income':
                category = request.form.get('income-category')

            amount = request.form['amount']
            if type == 'expense':
                amount = -float(amount)

            now = datetime.now()

            if current_year == now.year and current_month == now.month and current_day == now.day:
                transaction_date = now.strftime('%Y-%m-%d %H:%M:%S')
            else:
                transaction_date = datetime(current_year, current_month, current_day, 12, 0, 0).strftime('%Y-%m-%d %H:%M:%S')

            if not type or not amount or not user_id or not category:
                return {'error': 'Something went wrong'}, 401
            cur.execute("INSERT INTO transactions(type,amount,user_id,timestamp,category) VALUES(?,?,?,?,?)",(type, amount, user_id, transaction_date, category))
            get_db().commit()
            cur.close()

            return redirect(url_for('index', year=current_year, month=current_month, day=current_day))
        return render_template("index.html", txs=transactions, sum=sum, current_month=current_month, current_day=current_day, current_year=current_year, sum_by_categories=sum_by_categories)
    else:
        return redirect(url_for('login'))

@app.route('/expenses_by_category')
def expenses_by_category():
    if 'email' not in session:
        return jsonify({"error": "Not logged in"}), 401

    email = session["email"]
    user_id = get_user_id(email)[0]

    try:
        current_year = int(request.args.get('year'))
        current_month = int(request.args.get('month'))
        current_day = int(request.args.get('day'))
    except (TypeError, ValueError):
        return jsonify({"error": "Invalid date parameters"}), 400

    start_of_day = datetime(current_year, current_month, current_day)
    end_of_day = datetime(current_year, current_month, current_day, 23, 59, 59)
    cur = get_db().cursor()
    cur.execute("""
        SELECT category, SUM(amount)
        FROM transactions
        WHERE user_id=? AND type='expense' AND timestamp BETWEEN ? AND ?
        GROUP BY category
        """, (
            user_id,
            start_of_day.strftime('%Y-%m-%d %H:%M:%S'),
            end_of_day.strftime('%Y-%m-%d %H:%M:%S')
        ))
    data = cur.fetchall()
    cur.close()
    categories = [row[0] for row in data]
    amounts = [abs(row[1]) for row in data]
    return jsonify({"categories": categories, "amounts": amounts})

@app.route('/delete_tx', methods=['POST'])
def delete_tx():
    if 'email' not in session:
        return {'error': 'Not logged in'}, 401
    if 'email' in session:
        current_year = request.form.get('year')
        current_month = request.form.get('month')
        current_day = request.form.get('day')
        tx_id = request.form['tx_id']
        cur = get_db().cursor()
        cur.execute("DELETE FROM transactions WHERE id = ?", (tx_id,))
        get_db().commit()
        cur.close()
        return redirect(url_for('index', year=current_year, month=current_month, day=current_day))
    return 'You are not logged in'

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        email = request.form['email'].lower()
        password = request.form['password']
        if not email or not password:
            error='email and Password missing'
            return render_template('signup.html', error=error)
        
        if not email_validator(email):
            error = 'Invalid email'
            return render_template('signup.html', error=error)
        
        #encrypt password
        bytes = password.encode('utf-8')
        salt = bcrypt.gensalt()
        hash = bcrypt.hashpw(bytes, salt)

        #verification token
        verification_token = generate_token()

        #is verified
        is_verified = 0

        cur = get_db().cursor()
        cur.execute("SELECT * FROM users WHERE email = ?", (email,))
        check = cur.fetchone()
        
        if check is None:
            cur.execute("INSERT INTO users(email, password, is_verified, verification_token) VALUES(?,?,?,?)",(email,hash,is_verified,verification_token))
            get_db().commit()
            cur.close()

            send_verification_email(email, verification_token)
            error = 'Please verify your email'
            # session['email'] = email
            return render_template('login.html', error=error)
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
            current_year = datetime.now().year
            current_month = datetime.now().month
            current_day = datetime.now().day
            session['email'] = email
            return render_template('index.html', current_day=current_day, current_month=current_month, current_year=current_year)
        else:
            error = 'Invalid email or password'
            app.logger.warning(f'Failed login attempt - Incorrect password. Email: {email}')
            return render_template('login.html', error=error)
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('email', None)
    return redirect(url_for('login'))

@app.route('/verify')
def verify():
    token = request.args.get('token')

    if not token:
        return "Invalid verification link.", 400

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
        return "Invalid or expired verification token.", 404