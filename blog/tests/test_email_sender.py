import smtplib
from email.mime.application import MIMEApplication
from email.mime.image import MIMEImage
from email.mime.text import MIMEText
from unittest.mock import patch, Mock

import pytest

from common.send_email import (
    EmailWithAttachments,
    email_sender,
    EmailContent,
    WrongReceivedDataTypeException
)


class TestEmailWithAttachments:
    html_doc = """
               <!DOCTYPE html>
                <html lang="en">
                <head>
                    <meta charset="UTF-8">
                    <meta name="viewport" content="width=device-width, initial-scale=1.0">
                    <title>Test HTML Document</title>
                </head>
                <body>
                    <h1>Hello, World!</h1>
                </body>
                </html>
            """

    def test__create_mimetype_document(self):
        """
        Testing creating MIMEType documents such as plain text, html, image and file.
        """

        # test create plain text document
        actual_result = email_sender._create_mimetype_document(doc_type='plain_text', content='Some plain text')
        assert isinstance(actual_result, MIMEText)
        assert actual_result.get_payload() == 'Some plain text'

        # test create html document
        actual_result = email_sender._create_mimetype_document(doc_type='html', content=self.html_doc)
        assert isinstance(actual_result, MIMEText)
        assert actual_result.get_payload() == self.html_doc

        # test create image document
        with open('/home/sergey/PycharmProjects/Blog_FastAPI/blog/tests/avatar.png', 'rb') as image:
            actual_result = email_sender._create_mimetype_document(doc_type='image', content=image.read())

        assert isinstance(actual_result, MIMEImage)
        assert open(
            '/home/sergey/PycharmProjects/Blog_FastAPI/blog/tests/avatar.png',
            'rb').read() == actual_result.get_payload(decode=True)

        # test create file document
        with open('/home/sergey/PycharmProjects/Blog_FastAPI/blog/tests/sample-pdf-file.pdf', 'rb') as file:
            actual_result = email_sender._create_mimetype_document(doc_type='file', content=file.read())

        assert isinstance(actual_result, MIMEApplication)
        assert open('/home/sergey/PycharmProjects/Blog_FastAPI/blog/tests/sample-pdf-file.pdf',
                    'rb').read() == actual_result.get_payload(decode=True)

    def test__read_content(self):
        """
        Testing reading content from passed source.
        Source can be either path to file or file itself in str or bytes format.
        """

        # if content source is string (path to file)
        actual_result = email_sender._read_content(
            source='/home/sergey/PycharmProjects/Blog_FastAPI/blog/tests/avatar.png',
            type_media=True)
        assert isinstance(actual_result, bytes)

        # if content source is bytes (file itself in bytes format)
        actual_result = email_sender._read_content(source=self.html_doc.encode('utf-8'))
        assert isinstance(actual_result, str)
        assert actual_result == self.html_doc

        actual_result = email_sender._read_content(source='Some plain text'.encode('utf-8'))
        assert isinstance(actual_result, str)
        assert actual_result == 'Some plain text'

        # if file does not exist (by its path)
        with pytest.raises(FileNotFoundError) as exc:
            email_sender._read_content(source='wrong_path.png', type_media=True)

        assert exc.type == FileNotFoundError

        # if was passed not str or bytes type
        with pytest.raises(WrongReceivedDataTypeException) as exc:
            email_sender._read_content(source=123, type_media=True)

        assert exc.type == WrongReceivedDataTypeException
        assert exc.value.args[0] == (
            'Received unsupported data type. Allowed types are <str> and <bytes>, but type <int> was provided.'
        )

    @patch('blog.common.send_email.smtplib.SMTP_SSL')
    def test_send_mail(self, mock_smtp_ssl: Mock):
        """
        Testing sending email using SMTP library as a core.
        """

        sender = EmailWithAttachments(
            send_from='example@example.com',
            host='localhost',
            password='password'
        )

        # simulate that method `sendmail` could not transmit message
        mock_smtp_ssl.return_value.__enter__.return_value.sendmail.return_value = {
            'example@example.com': (550, b'User unknown')
        }

        with pytest.raises(smtplib.SMTPResponseException) as exc:
            sender.send_mail(
                send_to='example2@example.com',
                subject='Test',
                content=EmailContent(plain_text='Some plain text')
            )

        assert exc.type == smtplib.SMTPResponseException
        assert exc.value.args[0] == 550
        assert exc.value.args[1] == ('Check your email `example@example.com` for accuracy. '
                                     'Probably you made typo mistake or provided wrong address.')

        assert mock_smtp_ssl.return_value.__enter__.return_value.sendmail.call_count == 1

        # simulate that method `sendmail` was completed without any problem
        mock_smtp_ssl.return_value.__enter__.return_value.sendmail.return_value = None

        actual_result = sender.send_mail(
            send_to='example2@example.com',
            subject='Test',
            content=EmailContent(plain_text='Some plain text')
        )

        assert mock_smtp_ssl.return_value.__enter__.return_value.sendmail.call_count == 2

        assert actual_result == 'Successfully'

    def test__compose_email_attachments(self):
        """
        Testing returning dictionary with particular MIME type objects inside.
        It can be MIMEText, MIMEImage, MIMEApplication.
        """

        # add plain text
        email_content = EmailContent(plain_text='Just a simple plain text')
        actual_result = email_sender._compose_email_attachments(email_content)
        assert actual_result['plain_text'].as_string() == MIMEText('Just a simple plain text').as_string()

        # add html content
        email_content = EmailContent(html_name=self.html_doc.encode('utf-8'))
        actual_result = email_sender._compose_email_attachments(email_content)
        assert actual_result['html'].as_string() == MIMEText(_text=self.html_doc, _subtype='html').as_string()

        # add image content
        with open('/home/sergey/PycharmProjects/Blog_FastAPI/blog/tests/avatar.png', 'rb') as image:
            email_content = EmailContent(image_name='/home/sergey/PycharmProjects/Blog_FastAPI/blog/tests/avatar.png')
            actual_result = email_sender._compose_email_attachments(email_content)
            expected_result = MIMEImage(image.read())
            expected_result.add_header(
                'Content-Disposition',
                'attachment; filename=avatar.png'
            )
        assert actual_result['image'].as_bytes() == expected_result.as_bytes()
