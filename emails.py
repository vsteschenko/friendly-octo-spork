import os
from flask import current_app
import sib_api_v3_sdk
from sib_api_v3_sdk.rest import ApiException

configuration = sib_api_v3_sdk.Configuration()
configuration.api_key['api-key'] = os.getenv("BREVO_API_KEY")

def send_verification_email(email, token):
    base_url = current_app.config["BASE_URL"]
    new_url = f"{base_url}/verify?token={token}"
    api_instance = sib_api_v3_sdk.TransactionalEmailsApi(sib_api_v3_sdk.ApiClient(configuration))
    subject = "Verify your email"
    sender = {"name": "Ledger", "email": "slava@vsteschenko.me"}
    to = [{"email": email}]   
    html_content = f"""
    <html>
      <body>
        <p>Hi!</p>
        <p>Verify your email by clicking the link below:</p>
        <a href={new_url}>Verify Email</a>
      </body>
    </html>
    """

    send_smtp_email = sib_api_v3_sdk.SendSmtpEmail(
        to=to,
        sender=sender,
        subject=subject,
        html_content=html_content,
    )

    try:
        response = api_instance.send_transac_email(send_smtp_email)
        current_app.logger.info(f"Verification email sent to {email}. Message ID: {response.message_id}")
    except ApiException as e:
        current_app.logger.error(f"Failed to send verification email: {e}")

def send_reset_password_email(email, token):
    base_url = current_app.config["BASE_URL"]
    new_url = f"{base_url}/reset_password?token={token}"
    api_instance = sib_api_v3_sdk.TransactionalEmailsApi(sib_api_v3_sdk.ApiClient(configuration))
    subject = "Password Reset Request"
    sender = {"name": "Slava", "email": "slava@vsteschenko.me"}
    to = [{"email": email}]
    html_content = f"""
    <html>
      <body>
        <p>Hi!</p>
        <p>To reset your password, click the link below:</p>
        <a href={new_url}>Reset Password</a>
      </body>
    </html>
    """

    send_smtp_email = sib_api_v3_sdk.SendSmtpEmail(
        to=to,
        sender=sender,
        subject=subject,
        html_content=html_content,
    )

    try:
        response = api_instance.send_transac_email(send_smtp_email)
        current_app.logger.info(f"Password reset email sent to {email}. Message ID: {response.message_id}")
    except ApiException as e:
        current_app.logger.error(f"Failed to send password reset email: {e}")


def send_delete_account_email(email, token):
    base_url = current_app.config["BASE_URL"]
    new_url = f"{base_url}/delete_account?token={token}"
    api_instance = sib_api_v3_sdk.TransactionalEmailsApi(sib_api_v3_sdk.ApiClient(configuration))
    subject = "Ledger Delete Account Request"
    sender = {"name": "Slava", "email": "slava@vsteschenko.me"}
    to = [{"email": email}]
    html_content = f"""
    <html>
      <body>
        <p>Hi!</p>
        <p>You have requested to delete your account. This action is irreversible and will permanently remove all your data.</p>
        <p>To confirm account deletion, click the link below:</p>
        <a href={new_url}>Delete account</a>
      </body>
    </html>
    """

    send_smtp_email = sib_api_v3_sdk.SendSmtpEmail(
        to=to,
        sender=sender,
        subject=subject,
        html_content=html_content,
    )

    try:
        response = api_instance.send_transac_email(send_smtp_email)
        current_app.logger.info(f"Delete Account email sent to {email}. Message ID: {response.message_id}")
    except ApiException as e:
        current_app.logger.error(f"Failed to send delete account email: {e}")
