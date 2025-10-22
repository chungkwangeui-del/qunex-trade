import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
from dotenv import load_dotenv

load_dotenv()

def test_gmail_smtp():
    """Test Gmail SMTP connection"""
    mail_username = os.getenv('MAIL_USERNAME')
    mail_password = os.getenv('MAIL_PASSWORD')

    print(f"Testing Gmail SMTP with {mail_username}...")
    print(f"Password length: {len(mail_password) if mail_password else 0}")

    try:
        # Create message
        msg = MIMEMultipart()
        msg['From'] = mail_username
        msg['To'] = mail_username  # Send to self for testing
        msg['Subject'] = 'Test Email from Qunex Trade'

        body = 'This is a test email to verify SMTP configuration.'
        msg.attach(MIMEText(body, 'plain'))

        # Connect to Gmail SMTP server
        print("Connecting to smtp.gmail.com:587...")
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.set_debuglevel(1)  # Show debug output
        server.starttls()

        print(f"Logging in as {mail_username}...")
        server.login(mail_username, mail_password)

        print("Sending email...")
        server.send_message(msg)
        server.quit()

        print("✓ Email sent successfully!")
        return True

    except Exception as e:
        print(f"✗ Error: {e}")
        return False

if __name__ == '__main__':
    test_gmail_smtp()
