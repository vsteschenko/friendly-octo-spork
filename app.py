from flask import Flask, g
from dotenv import load_dotenv
import os
from datetime import datetime
import logging
from logging.handlers import RotatingFileHandler
from werkzeug.middleware.proxy_fix import ProxyFix
from config import DevelopmentConfig, ProductionConfig
from db import get_db
from emails import send_delete_account_email, send_reset_password_email, send_verification_email

load_dotenv()

app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

env = os.getenv("FLASK_ENV", "production").lower()

if env == "development":
    app.config.from_object(DevelopmentConfig)
else:
    app.config.from_object(ProductionConfig)

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