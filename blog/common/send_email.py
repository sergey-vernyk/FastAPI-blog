import smtplib
import ssl
from email.mime.application import MIMEApplication
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Sequence, Union, Literal, AnyStr

from jinja2 import FileSystemLoader, Environment

from config import get_settings
from settings.env_dirs import TEMPLATES_DIR_PATH

settings = get_settings()
environment = Environment(loader=FileSystemLoader(TEMPLATES_DIR_PATH))  # define templates location


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
        'image': MIMEImage
    }

    def __init__(self, send_from: str, host: str, password: str, port: int = 465) -> None:
        self.send_from = send_from
        self.port = port
        self.host = host
        self.password = password
        self._attachments_data = dict.fromkeys(['file', 'plain_text', 'html', 'image'], None)

    def _create_mimetype_document(self,
                                  doc_type: Literal['plain_text', 'html', 'file', 'image'],
                                  content: AnyStr) -> Union[MIMEText, MIMEImage, MIMEApplication]:
        """
        Returns MIME `doc_type` document created with `content`.
        """
        if doc_type == 'html':
            return self.mime_types[doc_type](_text=content, _subtype='html')

        return self.mime_types[doc_type](content)

    def _read_content(self,
                      source: AnyStr,
                      type_media: bool = False) -> str | FileNotFoundError | TypeError:
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

        raise TypeError(
            f'Received invalid data type. '
            f'Allowed types are <str> and <bytes>, but type <{type(source).__name__}> was provided'
        )

    def _compose_email_attachments(self,
                                   plain_text: AnyStr | None = None,
                                   html_name: AnyStr | None = None,
                                   file_name: str | None = None,
                                   image_name: str | None = None) -> dict:
        """
        Returns dict with attachment data for email.
        Data in dict are in particular MIME type which depends on their content.
        """
        # if no parameter has been sent
        if all([plain_text, html_name, file_name, image_name]) is None:
            raise ValueError('You must passed at least plain text for message\'s body')

        if plain_text is not None:
            document = None
            if isinstance(plain_text, bytes):
                content = self._read_content(plain_text)
                document = self._create_mimetype_document('plain_text', content)
            elif isinstance(plain_text, str):
                document = self._create_mimetype_document('plain_text', plain_text)

            self._attachments_data['plain_text'] = document

        if html_name:
            content = self._read_content(html_name)
            document = self._create_mimetype_document('html', content)
            self._attachments_data['html'] = document

        if file_name:
            content = self._read_content(file_name, type_media=True)
            file = self._create_mimetype_document('file', content)
            filename = file_name if '/' not in file_name else file_name.split('/')[-1]
            # add header as key/value pair to attachment part
            file.add_header(
                'Content-Disposition',
                f'attachment; filename={filename}',
            )
            self._attachments_data['file'] = file

        if image_name:
            content = self._read_content(image_name, type_media=True)
            image = self._create_mimetype_document('image', content)
            imagename = image_name if '/' not in image_name else image_name.split('/')[-1]
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

    def send_mail(self,
                  send_to: Sequence[str] | str,
                  subject: str,
                  bcc: Sequence[str] | str | None = None,
                  content: dict[
                               Literal['plain_text'], str | bytes,
                               Literal['html_name'], str | bytes,
                               Literal['file_name'], str,
                               Literal['image_name'], str
                           ] | None = None) -> smtplib.SMTPResponseException | Literal['Successfully']:
        """
        Send email over SSL.
        - `send_to` - email receivers,
        - `subject` - email subject,
        - `bcc` - blind carbon copy receivers,
        - `content` - dict with content for sending in format {key: value}:

            {'plain_text': text or bytes,
             'html_name': text html or bytes,
             'file_name': file name,
             'image_name': image name}

        Returns SMTPResponseException if there were any errors.
        """
        message = MIMEMultipart('alternative')
        message['Subject'] = subject
        message['From'] = self.send_from
        message['To'] = ', '.join(send_to) if isinstance(send_to, list) else send_to
        if isinstance(bcc, list):
            bcc = ', '.join(bcc)
        # attach parts to the message
        for att in self._compose_email_attachments(**content).values():
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
                msg=message.as_string()
            )
        if result:
            raise smtplib.SMTPResponseException(
                code=result.values()[0],
                msg=f'Check your email `{result.keys()[0]}` for accuracy. '
                    f'Probably you made typo mistake or provided wrong address.'
            )
        return 'Successfully'


email_sender = EmailWithAttachments(
    send_from=settings.email_from,
    host=settings.email_host,
    password=settings.email_password
)
