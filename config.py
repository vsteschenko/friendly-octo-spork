import os

class BaseConfig:
    SECRET_KEY = os.getenv("SECRET_KEY")
    DATABASE = os.getenv("DATABASE")
    WTF_CSRF_TIME_LIMIT = 3600
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    PERMANENT_SESSION_LIFETIME = 60 * 60 * 8
    TEMPLATES_AUTO_RELOAD = False
    DEBUG = False

class DevelopmentConfig(BaseConfig):
    DEBUG = True
    TEMPLATES_AUTO_RELOAD = True
    SESSION_COOKIE_SECURE = False
    PREFERRED_URL_SCHEME = "http"
    BASE_URL = "http://127.0.0.1:5000"

class ProductionConfig(BaseConfig):
    SESSION_COOKIE_SECURE = True
    PREFERRED_URL_SCHEME = "https"
    BASE_URL = "https://ledger.vsteschenko.me"