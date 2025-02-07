from flask import Flask, render_template, session, request, redirect, url_for, g
from dotenv import load_dotenv
import os, sqlite3, bcrypt


load_dotenv()
DATABASE = 'finance_app.db'

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


@app.route('/')
def index():
    if 'username' in session:
        return f'Logged in as {session["username"]}'
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
            return 'User registered successfully'
        else:
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
        session['username'] = request.form['username']
        username = request.form['username']
        password = request.form['password']
        
        cur = get_db().cursor()
        cur.execute("SELECT password FROM users WHERE username = ?", (username,))
        user = cur.fetchone()

        if user is None:
            return 'User not found'
        
        print(user[0])

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
    # remove the username from the session if it's there
    session.pop('username', None)
    return redirect(url_for('index'))
