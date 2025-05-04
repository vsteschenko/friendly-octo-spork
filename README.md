# Ledger Documentation

**Ledger** is an open-source personal finance tracking web application. It helps users track income and expenses, view reports, and analyze their finances over time — all with full control over their data.

---

## Features

- Add, edit, and delete income and expense records
- Categorize transactions
- Date-based filtering
- Monthly and yearly summaries
- Interactive charts via Chart.js
- Secure authentication with hashed passwords
- SQLite database (runs locally, no setup needed)

---

## Tech Stack

- **Backend:** Flask
- **Database:** SQLite
- **Frontend:** HTML, CSS, JavaScript
- **Authentication:** Flask + bcrypt

---

## Installation

1. **Clone the repo:**
git clone https://github.com/vsteschenko/friendly-octo-spork.git
cd friendly-octo-spork

2. **Create venv and install dependencies:**
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

3. **Create db:**
go 1 level up and run python3 create_db.py

4. **Create .env:**
Create a .env file in the root directory:
DATABASE="path to db"
SECRET_KEY="generate secret"

5. **Run ledger:**
flask run

Pull requests are welcome! Feel free to open issues or suggest features.