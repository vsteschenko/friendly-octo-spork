# Ledger Documentation

**Ledger** is a personal finance tracking web application. It helps me track income and expenses, and analyze my spending.

---

## Features

- Add, edit, and delete income and expense records
- Categorize transactions
- Monthly and yearly summaries

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