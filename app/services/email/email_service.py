import smtplib
from html import escape
from email.mime.text import MIMEText

from app.core.config import settings

email_from = settings.GOOGLE_EMAIL_FROM
password = settings.GOOGLE_EMAIL_PASSWORD


async def send_invite_email(to, group_name, invite_link):
    msg = MIMEText(invite_email_template(group_name, invite_link), "html")
    msg["Subject"] = "You've been invited to a group"
    await send_email(msg, to)


async def send_verification_email(to, link):
    msg = MIMEText(verification_email_template(link), "html")
    msg["Subject"] = "Email verification"
    await send_email(msg, to)


async def send_email(msg: MIMEText, to):
    msg["From"] = email_from
    msg["To"] = to

    with smtplib.SMTP("smtp.gmail.com", 587) as server:
        server.starttls()
        server.login(email_from, password)
        server.sendmail(msg["From"], msg["To"], msg.as_string())


def invite_email_template(group_name: str, invite_link: str) -> str:
    normalized_link = _normalize_absolute_url(invite_link)
    safe_group_name = escape(group_name)
    safe_link = escape(normalized_link, quote=True)

    return f"""
    <!DOCTYPE html>
    <html>
    <body style="font-family: Arial, sans-serif; background: #f4f4f4; padding: 40px;">
      <div style="max-width: 500px; margin: auto; background: white;
                  border-radius: 12px; padding: 40px; text-align: center;">

        <h2 style="color: #222; margin-bottom: 10px;">You've been invited to a group</h2>
        <p style="color: #666; font-size: 15px;">
          You have received an invitation to join <strong>{safe_group_name}</strong>
        </p>

        <a href="{safe_link}" target="_blank" rel="noopener noreferrer"
           style="display: inline-block;
                  background-color: #4F46E5;
                  color: white;
                  padding: 14px 36px;
                  text-decoration: none;
                  border-radius: 8px;
                  font-size: 16px;
                  font-weight: bold;
                  margin-top: 30px;
                  cursor: pointer;">
          Join Group
        </a>

        <p style="color: #bbb; font-size: 12px; margin-top: 30px;">
          If the button doesn't work, click the link below:<br>
          <a href="{safe_link}" target="_blank" rel="noopener noreferrer" style="color: #4F46E5; word-break: break-all;">{safe_link}</a>
        </p>

      </div>
    </body>
    </html>
    """

def verification_email_template(link: str) -> str:
    return f"""
    <!DOCTYPE html>
    <html>
    <body>
        <h1>Verify your email</h1>
        <p>Please click this <a href="{link}">link</a> to verify your email</p>
    </body>
    </html>
    
    """


def _normalize_absolute_url(link: str) -> str:
    value = (link or "").strip()
    if not value:
        return value
    if value.startswith(("http://", "https://")):
        return value
    return f"http://{value}"
