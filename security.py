from flask_wtf.csrf import CSRFProtect
from app import app

csrf = CSRFProtect(app)

CHARTJS = "https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/"
DATALABELS = "https://cdnjs.cloudflare.com/ajax/libs/chartjs-plugin-datalabels/2.2.0/"
FLATPICKR = "https://cdn.jsdelivr.net/npm/flatpickr@4.6.13/dist/"

@app.after_request
def add_security_headers(response):
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains; preload'
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = ("geolocation=(), microphone=(), camera=(), payment=(), usb=(), fullscreen=(self)")
    response.headers["Cross-Origin-Opener-Policy"] = "same-origin"
    response.headers["Cross-Origin-Resource-Policy"] = "same-origin"
    # Only the exact library versions the templates use may load from CDNs.
    # (A whole CDN domain would let an attacker load any script hosted there.)
    csp = (
        "default-src 'self'; "
        "script-src 'self' "
        f"{CHARTJS} {DATALABELS} {FLATPICKR}; "
        f"style-src 'self' {FLATPICKR} 'unsafe-inline'; "
        "img-src 'self' data:; "
        "font-src 'self' data:; "
        "object-src 'none'; "
        "connect-src 'self'; "
        "frame-ancestors 'none'; "
        "base-uri 'self'; "
        "form-action 'self'"
    )
    response.headers["Content-Security-Policy"] = csp
    return response