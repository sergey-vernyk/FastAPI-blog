import smtplib
import ssl
from email.mime.application import MIMEApplication
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Literal, NamedTuple, Sequence

from config import get_settings
from jinja2 import Environment, FileSystemLoader
from settings.env_dirs import TEMPLATES_DIR_PATH

settings = get_settings()
environment = Environment(loader=FileSystemLoader(TEMPLATES_DIR_PATH))  # define templates location


class WrongReceivedDataTypeException(Exception):
    """
    Raise this exception if was has been received unsupported data type.
    And there are no methods to handle received data type.
    """

    _message = 'Received unsupported data type. Allowed types are <str> and <bytes>, but type <{}> was provided.'

    def __init__(self, received_type):
        self.received_type = received_type
        self.message = self._message.format(type(received_type).__name__)
        super().__init__(self.message)


class EmailContent(NamedTuple):
    """
    Content for email body.
    """

    plain_text: str | bytes | None = None
    html_name: str | bytes | None = None
    file_name: str | None = None
    image_name: str | None = None

    def __bool__(self) -> bool:
        """
        Instance must have one attribute as not None at least to return True.
        """
        return any([self.plain_text, self.html_name, self.file_name, self.image_name])


class EmailWithAttachments:
    """
    Class for creating email with attachments like pictures, pdf documents, archives etc.
    Also with opportunity to add plain text along with HTML document in order to read email
    on devices without capable HTML.
    """

    # available MIME Types
    mime_types = {
        'plain_text': MIMEText,
        'html': MIMEText,
        'file': MIMEApplication,
        'image': MIMEImage,
    }

    def __init__(self, send_from: str, host: str, password: str, port: int = 465) -> None:
        self.send_from = send_from
        self.port = port
        self.host = host
        self.password = password
        self._attachments_data = dict.fromkeys(['file', 'plain_text', 'html', 'image'], None)

    def _create_mimetype_document(
        self,
        doc_type: Literal[Literal['plain_text'], Literal['html'], Literal['file'], Literal['image']],
        content: str | bytes,
    ) -> MIMEText | MIMEImage | MIMEApplication:
        """
        Returns MIME `doc_type` document created with `content`.
        """

        if doc_type == 'html':
            return self.mime_types[doc_type](_text=content, _subtype='html')

        return self.mime_types[doc_type](content)

    def _read_content(self, source: str | bytes, type_media: bool = False) -> str:
        """
        Read content from `source` taking in account its type.
        - `type_media` flag to recognize file type from passed `source` - media or text (False -> text),
           since reading files of different types is different.
        """
        if isinstance(source, str):
            # try to read file if it is existing
            try:
                with open(source, 'rb' if type_media else 'r', encoding=None if type_media else 'utf-8') as file:
                    return file.read()
            except FileNotFoundError as e:
                raise e
        # for html and plain text
        elif isinstance(source, bytes):
            return source.decode('utf-8')

        raise WrongReceivedDataTypeException(received_type=source)

    def _compose_email_attachments(self, attachments: EmailContent) -> dict:
        """
        Returns dict with attachment data for email.
        Data in dict are in particular MIME type which depends on their content.
        """
        if attachments.plain_text is not None:
            document = None
            if isinstance(attachments.plain_text, bytes):
                content = self._read_content(attachments.plain_text)
                document = self._create_mimetype_document('plain_text', content)
            elif isinstance(attachments.plain_text, str):
                document = self._create_mimetype_document('plain_text', attachments.plain_text)

            self._attachments_data['plain_text'] = document

        if attachments.html_name:
            content = self._read_content(attachments.html_name)
            document = self._create_mimetype_document('html', content)
            self._attachments_data['html'] = document

        if attachments.file_name:
            content = self._read_content(attachments.file_name, type_media=True)
            file = self._create_mimetype_document('file', content)
            filename = (
                attachments.file_name if '/' not in attachments.file_name else attachments.file_name.split('/')[-1]
            )
            # add header as key/value pair to attachment part
            file.add_header(
                'Content-Disposition',
                f'attachment; filename={filename}',
            )
            self._attachments_data['file'] = file

        if attachments.image_name:
            content = self._read_content(attachments.image_name, type_media=True)
            image = self._create_mimetype_document('image', content)
            imagename = (
                attachments.image_name if '/' not in attachments.image_name else attachments.image_name.split('/')[-1]
            )
            # add header as key/value pair to attachment part
            image.add_header(
                'Content-Disposition',
                f'attachment; filename={imagename}',
            )
            self._attachments_data['image'] = image

        return self._attachments_data

    def make_content_with_context(self, template_name: str, context: dict) -> bytes:
        """
        Returns html or plain with text with `template_name` in bytes format with passed `context`.
        """
        template = environment.get_template(template_name)
        return template.render(context).encode('utf-8')

    def send_mail(
        self, send_to: Sequence[str] | str, subject: str, content: EmailContent, bcc: Sequence[str] | str | None = None
    ) -> smtplib.SMTPResponseException | Literal['Successfully']:
        """
        Send email over SSL.
        - `send_to` - email receivers,
        - `subject` - email subject,
        - `bcc` - blind carbon copy receivers,
        - `content` - `EmailContent` typed tuple

        Returns `SMTPResponseException` if there were any errors.
        """
        message = MIMEMultipart('alternative')
        message['Subject'] = subject
        message['From'] = self.send_from
        message['To'] = ', '.join(send_to) if isinstance(send_to, list) else send_to
        if isinstance(bcc, list):
            bcc = ', '.join(bcc)
        # attach parts to the message
        for att in self._compose_email_attachments(content).values():
            if att is not None:
                message.attach(att)

        # create a secure SSL context
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL(host=self.host, port=self.port, context=context) as server:
            server.login(user=self.send_from, password=self.password)
            result = server.sendmail(
                # include receivers for bcc if any
                to_addrs=[send_to] + [bcc] if bcc else [send_to],
                from_addr=self.send_from,
                msg=message.as_string(),
            )
        if result:
            code = list(result.values())[0][0]
            msg = list(result.keys())[0]
            raise smtplib.SMTPResponseException(
                code=code,
                msg=f'Check your email `{msg}` for accuracy. '
                f'Probably you made typo mistake or provided wrong address.',
            )
        return 'Successfully'


email_sender = EmailWithAttachments(
    send_from=settings.email_from, host=settings.email_host, password=settings.email_password
)
