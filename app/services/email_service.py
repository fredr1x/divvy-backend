import os
import smtplib
from email.mime.text import MIMEText

email_from = os.getenv('GOOGLE_EMAIL_FROM')
password = os.getenv('GOOGLE_EMAIL_PASSWORD')

def send_invite_email(to, group_name, invite_link):
    msg = MIMEText(invite_email_template(group_name, invite_link), 'html')
    msg['Subject'] = 'You\'ve been invited to a group'
    msg['From'] = email_from
    msg['To'] = to

    with smtplib.SMTP('smtp.gmail.com', 587) as server:
        server.starttls()
        server.login(email_from, password)
        server.sendmail(msg['From'], msg['To'], msg.as_string())

def invite_email_template(group_name: str, invite_link: str) -> str:
    return f"""
    <!DOCTYPE html>
    <html>
    <body style="font-family: Arial, sans-serif; background: #f4f4f4; padding: 40px;">
      <div style="max-width: 500px; margin: auto; background: white;
                  border-radius: 12px; padding: 40px; text-align: center;">

        <h2 style="color: #222; margin-bottom: 10px;">You've been invited to a group</h2>
        <p style="color: #666; font-size: 15px;">
          You have received an invitation to join <strong>{group_name}</strong>
        </p>

        <a href="{invite_link}"
           style="display: inline-block;
                  background-color: #4F46E5;
                  color: white;
                  padding: 14px 36px;
                  text-decoration: none;
                  border-radius: 8px;
                  font-size: 16px;
                  font-weight: bold;
                  margin-top: 30px;">
          Join Group
        </a>

        <p style="color: #bbb; font-size: 12px; margin-top: 30px;">
          If the button doesn't work, click the link below:<br>
          <a href="{invite_link}" style="color: #4F46E5;">{invite_link}</a>
        </p>

      </div>
    </body>
    </html>
    """
