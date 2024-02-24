from smtplib import SMTPResponseException
from typing import Literal, Sequence

from celery_app import app
from common.send_email import email_sender


@app.task(name='send_user_email')
def send_email_to_user(context: dict,
                       html_template_location: str,
                       plain_text_template_location: str,
                       send_to: Sequence[str] | str) -> SMTPResponseException | Literal['Successfully']:
    """
    Send email to `send_to` email address with html document and
    plain text document, if users client does not capable with HTML.
    Returns `Successfully` if email has been sent successfully, raise SMTP exception otherwise.
    """
    html_content = email_sender.make_content_with_context(
        template_name=html_template_location,
        context=context
    )
    plain_text_content = email_sender.make_content_with_context(
        template_name=plain_text_template_location,
        context=context
    )
    return email_sender.send_mail(
        content={'plain_text': plain_text_content, 'html_name': html_content},
        send_to=send_to,
        subject=context['subject']
    )
