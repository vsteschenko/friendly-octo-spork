from flask_wtf.csrf import CSRFProtect
from app import app

csrf = CSRFProtect(app)

@app.after_request
def add_security_headers(response):
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains; preload'
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = ("geolocation=(), microphone=(), camera=(), payment=(), usb=(), fullscreen=(self)")
    response.headers["Cross-Origin-Opener-Policy"] = "same-origin"
    response.headers["Cross-Origin-Resource-Policy"] = "same-origin"
    csp = (
        "default-src 'self'; "
        "script-src 'self' "
        "https://cdn.jsdelivr.net "
        "https://cdn.jsdelivr.net/npm/chart.js "
        "https://cdnjs.cloudflare.com "
        "; "
        "style-src 'self' https://cdn.jsdelivr.net 'unsafe-inline'; "
        "img-src 'self' data:; "
        "font-src 'self' https://cdn.jsdelivr.net data:; "
        "connect-src 'self'; "
        "frame-ancestors 'none'; "
        "base-uri 'self'; "
        "form-action 'self'"
    )
    response.headers["Content-Security-Policy"] = csp
    return response