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
- **Email:** Brevo transactional API

---

## Running locally

1. **Clone the repo:**
   ```
   git clone https://github.com/vsteschenko/friendly-octo-spork.git
   cd friendly-octo-spork
   ```

2. **Create a venv and install dependencies:**
   ```
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt -r requirements-dev.txt
   ```

3. **Create `.env`** in the project folder (it is git-ignored, never commit it):
   ```
   FLASK_ENV=development
   DATABASE=ledger.db
   SECRET_KEY=<output of: python -c "import secrets; print(secrets.token_hex(32))">
   BCRYPT_ROUNDS=12
   BREVO_API_KEY=<optional locally; without it emails fail and are logged>
   # LOG_FILE=app.log   (optional: also write logs to a file)
   ```
   The database tables are created automatically on first start (see `schema.sql`).

4. **Run:** `flask run`

5. **Tests:** `pytest -q`

---

## Deploying

Pushing to `main` runs the tests and, if they pass, deploys over SSH
(`.github/workflows/deploy.yml`). Pull requests only run the tests.

**GitHub secrets** (Settings → Secrets and variables → Actions):

| Secret | Value |
|---|---|
| `VPS_HOST` | server IP or hostname |
| `VPS_USER` | SSH user that deploys |
| `VPS_SSH_KEY` | private key used only for deploys |
| `VPS_KNOWN_HOSTS` | output of `ssh-keyscan -H <server>` (check the fingerprint matches the server) |

**On the server**, the env file `~/ledger/env/ledger.env` holds `DATABASE=/data/<name>.db`,
`SECRET_KEY`, `BCRYPT_ROUNDS` and `BREVO_API_KEY`, readable only by the owner (`chmod 600`).
Add `LOG_FILE=/data/app.log` to keep logs across redeploys.

The container runs as an unprivileged user with UID 1000, so the data folder must be
owned by that UID: `sudo chown -R 1000:1000 ~/ledger/data`.

**Brevo API keys expire after 90 days without use.** If the app sends no emails for a
long time, send yourself a password reset now and then, or the key has to be rotated.

---

Pull requests are welcome! Feel free to open issues or suggest features.
