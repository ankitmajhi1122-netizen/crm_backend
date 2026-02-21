"""
email_utils.py — SMTP email sender via Gmail.
"""
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

load_dotenv()

SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_FROM = os.getenv("SMTP_FROM", SMTP_USER)


def send_email(to: str, subject: str, body_html: str) -> None:
    """
    Send an HTML email via Gmail SMTP (TLS).
    Raises smtplib.SMTPException on failure.
    """
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = SMTP_FROM
    msg["To"] = to

    part = MIMEText(body_html, "html")
    msg.attach(part)

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.ehlo()
        server.starttls()
        server.login(SMTP_USER, SMTP_PASSWORD)
        server.sendmail(SMTP_FROM, [to], msg.as_string())


def send_password_reset_email(to: str, reset_token: str, frontend_url: str) -> None:
    reset_link = f"{frontend_url}/reset-password?token={reset_token}"
    subject = "CRM — Password Reset Request"
    body = f"""
    <html><body>
    <h2>Password Reset</h2>
    <p>Click the link below to reset your CRM password. This link expires in 1 hour.</p>
    <p><a href="{reset_link}" style="background:#6366f1;color:#fff;padding:10px 20px;border-radius:6px;text-decoration:none;">
       Reset Password
    </a></p>
    <p>If you did not request a password reset, ignore this email.</p>
    </body></html>
    """
    send_email(to, subject, body)


def send_welcome_email(to: str, name: str, temp_password: str) -> None:
    subject = "Welcome to CRM — Your Account Details"
    body = f"""
    <html><body>
    <h2>Welcome, {name}!</h2>
    <p>Your CRM account has been created by your administrator.</p>
    <p><strong>Email:</strong> {to}<br>
       <strong>Temporary Password:</strong> {temp_password}</p>
    <p>Please log in and change your password immediately.</p>
    </body></html>
    """
    send_email(to, subject, body)
