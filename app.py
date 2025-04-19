from flask import Flask, render_template, session, request, redirect, url_for, g, jsonify
from dotenv import load_dotenv
import os, sqlite3, bcrypt
from datetime import datetime

load_dotenv()
DATABASE = os.getenv("DATABASE")

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY")

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def get_user_id(username):
    cur = get_db().cursor()
    cur.execute("SELECT id FROM users WHERE username = ?",(username,))
    user_id = cur.fetchone()
    return user_id

@app.route('/', methods=['GET', 'POST'])
def index():
    if 'username' in session:
        username = session["username"]
        user_id = get_user_id(username)[0]

        current_year = datetime.now().year
        current_month = datetime.now().month

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
        
        start_of_month = datetime(current_year, current_month, 1).strftime('%Y-%m-%d %H:%M:%S')
        if current_month == 12:
            end_of_month = datetime(current_year + 1, 1, 1).strftime('%Y-%m-%d %H:%M:%S')
        else:
            end_of_month = datetime(current_year, current_month + 1, 1).strftime('%Y-%m-%d %H:%M:%S')

        # fetch transactions for the current month
        cur = get_db().cursor()
        cur.execute("""
            SELECT transactions.amount, transactions.type, transactions.id, transactions.timestamp, transactions.category 
            FROM transactions JOIN users ON transactions.user_id=users.id 
            WHERE users.id = ? AND transactions.timestamp BETWEEN ? AND ?
            """, (user_id, start_of_month, end_of_month))
        transactions = cur.fetchall()

        cur.execute("SELECT category, SUM(amount) FROM transactions JOIN users ON transactions.user_id=users.id WHERE user_id=? AND  type='expense' AND timestamp BETWEEN ? AND ? GROUP BY category;",(user_id,start_of_month,end_of_month))
        sum_by_categories = cur.fetchall()

        # sum for the current month
        cur.execute("SELECT SUM(amount) FROM transactions WHERE user_id=? AND timestamp BETWEEN ? AND ?", (user_id, start_of_month, end_of_month))
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

            if current_year == now.year and current_month == now.month:
                transaction_date = now.strftime('%Y-%m-%d %H:%M:%S')
            else:
                transaction_date = datetime(current_year, current_month, 1, 12, 0, 0).strftime('%Y-%m-%d %H:%M:%S')

            if not type or not amount or not user_id or not category:
                return {'error': 'Something went wrong'}, 401
            cur.execute("INSERT INTO transactions(type,amount,user_id,timestamp,category) VALUES(?,?,?,?,?)",(type, amount, user_id, transaction_date,category))
            get_db().commit()
            cur.close()

            return redirect(url_for('index', year=current_year, month=current_month))
        return render_template("index.html", txs=transactions, sum=sum, current_month=current_month, current_year=current_year, sum_by_categories=sum_by_categories)
    return 'You are not logged in'

@app.route('/expenses_by_category')
def expenses_by_category():
    if 'username' in session:
        username = session["username"]
        user_id = get_user_id(username)[0]

        current_year = request.args.get('year', datetime.now().year, type=int)
        current_month = request.args.get('month', datetime.now().month, type=int)

        start_of_month = datetime(current_year, current_month, 1).strftime('%Y-%m-%d %H:%M:%S')
        end_of_month = datetime(current_year, current_month + 1, 1).strftime('%Y-%m-%d %H:%M:%S') if current_month < 12 else datetime(current_year + 1, 1, 1).strftime('%Y-%m-%d %H:%M:%S')

        cur = get_db().cursor()
        cur.execute("SELECT category, SUM(amount) FROM transactions WHERE user_id=? AND type='expense' AND timestamp BETWEEN ? AND ? GROUP BY category", (user_id, start_of_month, end_of_month))

        data = cur.fetchall()
        cur.close()

        categories = [row[0] for row in data]
        amounts = [abs(row[1]) for row in data]

        return jsonify({"categories": categories, "amounts": amounts})

    return jsonify({"error": "Not logged in"}), 401

@app.route('/delete_tx', methods=['POST'])
def delete_tx():
    if 'username' not in session:
        return {'error': 'Not logged in'}, 401
    if 'username' in session:
        current_year = request.args.get('year')
        current_month = request.form.get('month')
        tx_id = request.form['tx_id']
        cur = get_db().cursor()
        cur.execute("DELETE FROM transactions WHERE id = ?", (tx_id,))
        get_db().commit()
        cur.close()
        return redirect(url_for('index', year=current_year, month=current_month))
    return 'You are not logged in'

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        #encrypt password
        bytes = password.encode('utf-8')
        salt = bcrypt.gensalt()
        hash = bcrypt.hashpw(bytes, salt)

        cur = get_db().cursor()
        cur.execute("SELECT * FROM users WHERE username = ?", (username,))
        check = cur.fetchone()
        
        if check is None:
            # create a user
            cur.execute("INSERT INTO users(username, password) VALUES(?,?)",(username,hash,))
            get_db().commit()
            cur.close()
            
            session['username'] = username
            return redirect(url_for('index'))
        else:
            cur.close()
            return 'User exists'
    return """
        <form method="post">
            <p><input type=text name=username>
            <p><input type=password name=password>
            <p><input type=submit value=Login>
        </form>
    """

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        cur = get_db().cursor()
        cur.execute("SELECT password FROM users WHERE username = ?", (username,))
        user = cur.fetchone()
        cur.close()

        if not user:
            return 'User not found', 404

        if bcrypt.checkpw(password.encode('utf-8'), user[0]):
            session['username'] = username
            return redirect(url_for('index'))
        else:
            return 'Invalid password', 401

    return """
        <form method="post">
            <p><input type=text name=username>
            <p><input type=password name=password>
            <p><input type=submit value=Login>
        </form>
    """

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('index'))