import os
from urllib.parse import quote
from flask import current_app
import sib_api_v3_sdk
from sib_api_v3_sdk.rest import ApiException

SENDER_EMAIL = "slava@vsteschenko.me"


def _send(email, subject, sender_name, body_html, log_label):
    # Read the key when sending (not at import time) so it is always the
    # current value from the environment / .env file.
    configuration = sib_api_v3_sdk.Configuration()
    configuration.api_key['api-key'] = os.getenv("BREVO_API_KEY")
    api_instance = sib_api_v3_sdk.TransactionalEmailsApi(sib_api_v3_sdk.ApiClient(configuration))

    message = sib_api_v3_sdk.SendSmtpEmail(
        to=[{"email": email}],
        sender={"name": sender_name, "email": SENDER_EMAIL},
        subject=subject,
        html_content=f"<html><body>{body_html}</body></html>",
    )
    try:
        response = api_instance.send_transac_email(message)
        current_app.logger.info(f"{log_label} email sent to {email}. Message ID: {response.message_id}")
    except ApiException as e:
        # Log only the status: the full exception can include request details.
        current_app.logger.error(f"Failed to send {log_label} email to {email}: HTTP {getattr(e, 'status', '?')} {getattr(e, 'reason', '')}")
    except Exception as e:
        # Network errors etc. must not turn signup/reset into a 500 page.
        current_app.logger.error(f"Failed to send {log_label} email to {email}: {type(e).__name__}")


def send_verification_email(email, token):
    url = f"{current_app.config['BASE_URL']}/verify?token={quote(token)}"
    _send(email, "Verify your email", "Ledger",
          f'<p>Hi!</p><p>Verify your email by clicking the link below:</p><a href="{url}">Verify Email</a>',
          "Verification")


def send_reset_password_email(email, token):
    url = f"{current_app.config['BASE_URL']}/reset_password?token={quote(token)}"
    _send(email, "Password Reset Request", "Slava",
          f'<p>Hi!</p><p>To reset your password, click the link below:</p><a href="{url}">Reset Password</a>'
          '<p>If you did not ask for this, you can ignore this email.</p>',
          "Password reset")


def send_delete_account_email(email, token):
    url = f"{current_app.config['BASE_URL']}/delete_account?token={quote(token)}"
    _send(email, "Ledger Delete Account Request", "Slava",
          '<p>Hi!</p><p>You have requested to delete your account. This action is irreversible and will '
          'permanently remove all your data.</p><p>To confirm account deletion, click the link below:</p>'
          f'<a href="{url}">Delete account</a>',
          "Delete account")


def send_account_exists_email(email):
    base = current_app.config['BASE_URL']
    _send(email, "You already have a Ledger account", "Ledger",
          '<p>Hi!</p><p>Someone tried to sign up for Ledger with this email, but you already have an account.</p>'
          f'<p><a href="{base}/login">Log in</a> or, if you forgot your password, '
          f'<a href="{base}/forgot_password">reset it</a>.</p>'
          '<p>If this wasn\'t you, you can ignore this email.</p>',
          "Account exists")
