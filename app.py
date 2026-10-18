from dotenv import load_dotenv
# Load .env before importing config, which reads environment variables.
load_dotenv()

from flask import Flask, g
from flask.logging import default_handler
import os
import re
from datetime import datetime
import logging
from logging.handlers import RotatingFileHandler
from werkzeug.middleware.proxy_fix import ProxyFix
from config import DevelopmentConfig, ProductionConfig
from db import get_db

app = Flask(__name__)
# Trust exactly one proxy (nginx) for the client IP, scheme and host.
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

env = os.getenv("FLASK_ENV", "production").lower()

if env == "development":
    app.config.from_object(DevelopmentConfig)
else:
    app.config.from_object(ProductionConfig)

if not app.config.get("SECRET_KEY"):
    raise RuntimeError("SECRET_KEY is not set. Add it to your .env / env file.")

EMAIL_RE = re.compile(r"([A-Za-z0-9._%+-]{1,2})[A-Za-z0-9._%+-]*@([A-Za-z0-9.-]+\.[A-Za-z]{2,})")

class MaskEmails(logging.Filter):
    """Logs keep only the first 2 letters of an email: alice@x.com -> al***@x.com."""
    def filter(self, record):
        record.msg = EMAIL_RE.sub(r"\1***@\2", record.getMessage())
        record.args = None
        return True

formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
handlers = [logging.StreamHandler()]  # visible with `docker compose logs`
# Optional file log. In Docker, point it at the data volume (e.g. LOG_FILE=/data/app.log)
# so it survives container rebuilds.
if os.getenv("LOG_FILE"):
    handlers.append(RotatingFileHandler(os.getenv("LOG_FILE"), maxBytes=10_000_000, backupCount=3))
app.logger.removeHandler(default_handler)  # Flask's own handler would log unmasked duplicates
for handler in handlers:
    handler.setFormatter(formatter)
    handler.addFilter(MaskEmails())
    app.logger.addHandler(handler)
app.logger.setLevel(logging.INFO)

@app.template_filter('datetimeformat')
def datetimeformat(value, format='%H:%M'):
    dt = datetime.strptime(value, '%Y-%m-%d %H:%M:%S')
    return dt.strftime(format)

@app.template_filter('currency')
def currency_format(value):
    if value is None:
        return "0.00"
    return "{:.2f}".format(float(value))

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

from CRUD import user, transactions
import security