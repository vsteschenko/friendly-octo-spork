from flask import Flask, render_template, session, request, redirect, url_for, g
from dotenv import load_dotenv
import os, sqlite3, bcrypt


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
        
        cur = get_db().cursor()
        cur.execute("SELECT transactions.amount, transactions.type, transactions.id, transactions.timestamp FROM transactions JOIN users ON transactions.user_id=users.id WHERE username = ?", (username,))
        transactions = cur.fetchall()
        
        cur.execute("SELECT SUM(amount) FROM transactions WHERE user_id=?",(user_id,))
        sum = cur.fetchone()[0]

        if request.method == 'POST':
            type = request.form['type']
            amount = request.form['amount']
            cur.execute("INSERT INTO transactions(type,amount,user_id) VALUES(?,?,?)",(type, amount, user_id,))
            get_db().commit()
            cur.close()

            return redirect(url_for('index'))
        return render_template("index.html", txs=transactions, sum=sum)
    return 'You are not logged in'

@app.route('/delete_tx', methods=['POST'])
def delete_tx():
    if 'username' in session:
        tx_id = request.form['tx_id']
        cur = get_db().cursor()
        cur.execute("DELETE FROM transactions WHERE id = ?", (tx_id,))
        get_db().commit()
        cur.close()
        return redirect(url_for('index'))
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

        return 'some message'
    return '''
        <form method="post">
            <p><input type=text name=username>
            <p><input type=password name=password>
            <p><input type=submit value=Login>
        </form>
    '''

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        cur = get_db().cursor()
        cur.execute("SELECT password FROM users WHERE username = ?", (username,))
        user = cur.fetchone()
        cur.close()

        if user is None:
            return 'User not found'

        if bcrypt.checkpw(password.encode('utf-8'), user[0]):
            session['username'] = username
            return redirect(url_for('index'))
        else:
            return 'Invalid password'

    return '''
        <form method="post">
            <p><input type=text name=username>
            <p><input type=password name=password>
            <p><input type=submit value=Login>
        </form>
    '''

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('index'))