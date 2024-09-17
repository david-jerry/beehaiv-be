from src.app.auth.models import BankAccount, User, Card
from src.celery_tasks import send_email

async def send_blocked_email(user: User, code: str, domain: str):
    subject = "Email Verification"
    body = f"""
    <html>
        <body>
            <p>Hello {user.first_name},</p>
            <p>We are sorry you are experiencing any form of dissatisfaction, however please treat this with urgency so you can continue using our services.</p>
            <p>Your account has been suspended for suspected transaction and authorization</p>
            <p>Please come in person to verify your credentials and further questioning.</p>

        </body>
    </html>
    """
    send_email.apply_async(args=[[user.email], subject, body])


async def send_verification_email(user: User, code: str, domain: str):
    subject = "Email Verification"
    body = f"""
    <html>
        <body>
            <p>Hello {user.first_name},</p>
            <p>Your verification code is:<a href="http://{domain}/accounts/reset_password?code={code}">{code}</a></p>
            <p>Please use this code to verify your email address.</p>
        </body>
    </html>
    """
    send_email.apply_async(args=[[user.email], subject, body])

async def send_reset_password_email(user: User, domain: str, reset_code: str):
    subject = "Reset Your Password"
    body = f"""
    <html>
        <body>
            <p>Hello {user.first_name},</p>
            <p>Your password reset code is: <a href="http://{domain}/accounts/reset_password?code={reset_code}">{reset_code}</a></p>
            <p>Please use this code to reset your password.</p>
        </body>
    </html>
    """
    send_email.apply_async(args=[[user.email], subject, body])

async def send_card_pin(user: User, card: Card):
    subject = "Debit Card PIN"
    body = f"""
    <html>
        <body>
            <p>Hello {user.first_name},</p>
            <p>Your Debit Card - {card.card_number} pin is: <strong>{card.pin}</strong>
            <p>Please remember to switch the pin.</p>
        </body>
    </html>
    """
    send_email.apply_async(args=[[user.email], subject, body])

async def send_new_bank_account_details(user: User, bank: BankAccount):
    subject = "New Bank Account"
    body = f"""
    <html>
        <body>
            <p>Hello {user.first_name},</p>
            <p>Your bank details:</p>
            <p>Bank Type: {bank.account_type}</p>
            <p>Bank Name: {bank.bank_name}</p>
            <p>Bank Account No: {bank.account_number}</p>
            <p>Bank Sort Code: {bank.sort_code}</p>
            <p>Bank Router: {bank.routing_number}</p>
            <p>Please remember to use this details when receiving and sending international and domestic transactions.</p>
        </body>
    </html>
    """
    send_email.apply_async(args=[[user.email], subject, body])

async def send_notification_email(user: User, message: str):
    subject = "Notification"
    body = f"Hello {user.first_name},\n\n{message}"
    send_email.apply_async(args=[[user.email], subject, body])
