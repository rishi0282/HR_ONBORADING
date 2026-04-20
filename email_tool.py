from fastmcp import FastMCP
from mcp.types import TextContent
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv
import os
load_dotenv()
mcp = FastMCP("GeneralEmailServer")
SENDER_EMAIL = os.getenv("SENDER_EMAIL")
SENDER_PASSWORD = os.getenv("SENDER_PASSWORD")
@mcp.tool()
def send_email(
    recipient_email: str,
    subject: str,
    body: str
) -> list[TextContent]:
    """
    Sends a general email to any recipient.
    Args:
        recipient_email (str): Recipient's email address
        subject (str): Email subject
        body (str): Email body content
    Returns:
        list[TextContent]: Success or error message
    """
    try:
        message = MIMEMultipart()
        message['From'] = SENDER_EMAIL
        message['To'] = recipient_email
        message['Subject'] = subject
        message.attach(MIMEText(body, 'plain'))
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.send_message(message)
        server.quit()
        return [TextContent(
            type="text",
            text=f"✅ Email sent successfully!\n\n"
                 f"From: {SENDER_EMAIL}\n"
                 f"To: {recipient_email}\n"
                 f"Subject: {subject}"
        )]
    except Exception as e:
        return [TextContent(
            type="text",
            text=f"❌ Error sending email: {str(e)}"
        )]
@mcp.tool()
def send_bulk_emails(
    recipients: str,
    subject: str,
    body: str
) -> list[TextContent]:
    """
    Sends emails to multiple recipients (comma-separated).
    Args:
        recipients (str): Comma-separated email addresses
        subject (str): Email subject
        body (str): Email body content
    Returns:
        list[TextContent]: Summary of sent emails
    """
    try:
        email_list = [email.strip() for email in recipients.split(',')]
        sent_count = 0
        failed_emails = []
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        for recipient in email_list:
            try:
                message = MIMEMultipart()
                message['From'] = SENDER_EMAIL
                message['To'] = recipient
                message['Subject'] = subject
                message.attach(MIMEText(body, 'plain'))
                server.send_message(message)
                sent_count += 1
            except Exception as e:
                failed_emails.append(f"{recipient} ({str(e)})")
        server.quit()
        result = f"✅ Bulk email sending completed!\n\n"
        result += f"Total: {len(email_list)} | Sent: {sent_count} | Failed: {len(failed_emails)}\n"
        if failed_emails:
            result += f"\nFailed:\n" + "\n".join(f"  - {f}" for f in failed_emails)
        return [TextContent(type="text", text=result)]
    except Exception as e:
        return [TextContent(
            type="text",
            text=f"❌ Error: {str(e)}"
        )]
if __name__ == "__main__":
    mcp.run(transport="sse",host="0.0.0.0",port="8080")
