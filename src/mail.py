from fastapi_mail import FastMail, ConnectionConfig, MessageSchema, MessageType
from src.config.settings import Config
from pathlib import Path
from typing import Optional, List, Union



# Configure FastMail with the necessary settings
mail_config = ConnectionConfig(
    MAIL_USERNAME=Config.MAIL_USERNAME,
    MAIL_PASSWORD=Config.MAIL_PASSWORD,
    MAIL_FROM=Config.MAIL_FROM,
    MAIL_PORT=Config.MAIL_PORT,
    MAIL_SERVER=Config.MAIL_SERVER,
    MAIL_FROM_NAME=Config.MAIL_FROM_NAME,
    MAIL_STARTTLS=Config.MAIL_STARTTLS or False,
    MAIL_SSL_TLS=Config.MAIL_SSL_TLS or False,
    USE_CREDENTIALS=Config.USE_CREDENTIALS or False,
    VALIDATE_CERTS=Config.VALIDATE_CERTS or False,
    TEMPLATE_FOLDER=Path(Config.BASE_DIR, "src/templates"),  # Uncomment if you have templates to use
)

# Initialize FastMail with the configuration
mail = FastMail(config=mail_config)

def create_message(
    recipients: List[str],
    subject: str,
    body: str,
    attachments: Optional[List[Union[Path, dict]]] = None
) -> MessageSchema:
    """
    Creates an email message with optional attachments.

    :param recipients: List of recipient email addresses
    :param subject: Subject of the email
    :param body: Body of the email, can be plain text or HTML
    :param attachments: Optional list of attachments. Attachments can be provided as file paths (Path objects)
                        or dictionaries with 'filename', 'file', and 'mime_type' keys.
    :return: Configured MessageSchema object ready to be sent
    """
    # Prepare the attachments if provided
    formatted_attachments = []
    if attachments:
        for attachment in attachments:
            if isinstance(attachment, Path):
                # Handle file paths
                formatted_attachments.append(
                    {"file": attachment.read_bytes(), "filename": attachment.name}
                )
            elif isinstance(attachment, dict):
                # Handle raw content provided in a dictionary format
                formatted_attachments.append(
                    {
                        "file": attachment["file"],
                        "filename": attachment.get("filename", "attachment"),
                        "mime_type": attachment.get("mime_type", "application/octet-stream"),
                    }
                )

    # Create the message with attachments
    message = MessageSchema(
        recipients=recipients,
        subject=subject,
        body=body,
        subtype=MessageType.html,  # Change to MessageType.plain if sending plain text
        attachments=formatted_attachments
    )

    return message

async def send_email(recipients: List[str], subject: str, body: str, attachments: Optional[List[Union[Path, dict]]] = None):
    """
    Sends an email with the specified subject, body, and optional attachments.

    :param recipients: List of recipient email addresses
    :param subject: Email subject
    :param body: Email body content
    :param attachments: List of attachments as file paths or content dicts
    """
    message = create_message(recipients, subject, body, attachments)
    await mail.send_message(message)
    print("Email sent successfully")
