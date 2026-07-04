from flask import request, render_template, session, redirect, url_for, jsonify
from app import app
from utils.utils import get_user_id
from datetime import datetime
from calendar import monthrange
from db import get_db
from utils.categories import category_name, income_category_name

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
            SELECT transactions.amount, transactions.type, transactions.id, transactions.timestamp, transactions.category, transactions.place, transactions.comment
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
            comment = request.form['comment']
            hour, minute = map(int, time.split(':'))
            transaction_date = datetime(current_year, current_month, current_day, hour, minute)
            if len(place) > 100:
                return {'error': 'Name of the place is too long'}, 404
            if len(comment) > 250:
                return {'error': 'Comment is too long'}, 404
            if type == 'expense':
                category = request.form.get('expense-category')
            elif type == 'income':
                category = request.form.get('income-category')

            amount = request.form['amount']
            if type == 'expense':
                amount = -float(amount)

            if not type or not amount or not user_id or not category or not transaction_date:
                return {'error': 'Select category'}, 401
            cur.execute("INSERT INTO transactions(type,amount,user_id,timestamp,category,place,comment) VALUES(?,?,?,?,?,?,?)",(type, amount, user_id, transaction_date, category, place, comment))
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
    cur.execute("SELECT category, SUM(amount) FROM transactions WHERE user_id=? AND type='income' AND timestamp LIKE ? GROUP BY category", (user_id, timestamp_pattern))
    income_by_category = cur.fetchall()
    new_income_by_category = []
    for cat in income_by_category:
        x = income_category_name[cat[0]]
        new_tx = (cat[0], cat[1], x)
        new_income_by_category.append(new_tx)
    income_by_category = new_income_by_category
    return render_template('annual_report.html', current_year=year, current_month=month, username=username, expense=expense, income=income, sum_by_category=sum_by_category, income_by_category=income_by_category)

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
        comment = request.form['comment']
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
        if len(comment) > 250:
            return {'error': 'Comment is too long'}, 400
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
            SET type = ?, place = ?, amount = ?, category = ?, timestamp = ?, comment = ?
            WHERE id = ? AND user_id = ?
        """, (type, place, amount, category, transaction_date, comment, tx_id, user_id))
        get_db().commit()
        cur.close()

        app.logger.info(f'{email} -- updated transaction {tx_id}')

        return redirect(url_for('index', year=current_year, month=current_month, day=current_day))
    return redirect(url_for('login'))

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
    type = request.args.get("type", "expense")
    if type not in ("expense", "income"):
        return jsonify({"error": "invalid type"}), 400
    
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
          AND type=?
          AND category=?
          AND timestamp BETWEEN ? AND ?
        ORDER BY timestamp ASC
        """,
        (user_id, type, category, start_of_year, end_of_year),
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

@app.route('/search', methods=['GET'])
def search_transactions():
    if 'email' not in session:
        return redirect(url_for('login'))

    email = session["email"]
    username = email.split("@")[0]
    user_id = get_user_id(email)

    if user_id is None:
        return redirect(url_for('login'))

    query = request.args.get('q', '', type=str).strip()
    transactions = []
    error = None

    if len(query) > 80:
        error = "Search is too long"
    elif query and len(query) < 2:
        error = "Please enter at least 2 characters"
    elif query:
        cur = get_db().cursor()
        cur.execute("""
            SELECT amount, type, id, timestamp, category, place, comment
            FROM transactions
            WHERE user_id = ?
              AND place IS NOT NULL
              AND place != ''
              AND place LIKE ? COLLATE NOCASE
            ORDER BY timestamp DESC, id DESC
            LIMIT 100
        """, (user_id, f"{query}%"))
        transactions = cur.fetchall()
        cur.close()

        app.logger.info(f'{email} -- searched transactions by place')

    return render_template(
        'search.html',
        txs=transactions,
        query=query,
        error=error,
        username=username
    )