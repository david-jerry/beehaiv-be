import asyncio
from celery import Celery
from src.mail import mail, create_message
from src.config.settings import Config
from src.utils.logger import LOGGER

# Initialize Celery with autodiscovery
celery_app = Celery(
    "beehaiv",
    broker=Config.CELERY_BROKER_URL,
    backend=Config.REDIS_URL,
)
celery_app.config_from_object(Config)

# Autodiscover tasks from all installed apps (each app should have a 'tasks.py' file)
celery_app.autodiscover_tasks(packages=['src.app.auth', 'src.app.blogs', 'src.app.loans', 'src.app.transactions'], related_name='tasks')

@celery_app.task(bind=True)
def send_email(self, recipients: list[str], subject: str, body: str, attachments: list[dict] = None):
    """
    Celery task to send emails with optional attachments asynchronously.

    :param recipients: List of recipient email addresses
    :param subject: Subject of the email
    :param body: Body of the email
    :param attachments: List of attachments in the format {'filename': <filename>, 'content': <file content>, 'mime_type': <mime type>}
    """
    try:
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            loop.create_task(send_email_async(recipients, subject, body, attachments))
        else:
            # Run the asynchronous email sending function
            asyncio.run(send_email_async(recipients, subject, body, attachments))
        LOGGER.info("Email sent successfully")
    except Exception as exc:
        # Log the error and retry if necessary
        LOGGER.error(f"Error sending email: {exc}")
        self.retry(exc=exc, countdown=60)  # Retry after 60 seconds if the task fails


async def send_email_async(recipients: list[str], subject: str, body: str, attachments: list[dict] = None):
    # Create the email message
    message = create_message(recipients=recipients, subject=subject, body=body)

    # Attach files if any
    if attachments:
        for attachment in attachments:
            message.attach(
                filename=attachment['filename'],
                data=attachment['content'],
                content_type=attachment.get('mime_type', 'application/octet-stream')  # Default MIME type if not specified
            )

    # Send the email asynchronously (replace this with the actual async method you're using)
    await mail.send_message(message)  # Example placeholder for actual async send method


