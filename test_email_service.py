"""
Tests for the email service CC and HTML functionality.
"""

import unittest
from unittest.mock import MagicMock, patch
from email_service import build_message, send_email, _normalize_addresses


class TestNormalizeAddresses(unittest.TestCase):
    def test_none_returns_empty_list(self):
        self.assertEqual(_normalize_addresses(None), [])

    def test_single_string_returns_list(self):
        self.assertEqual(_normalize_addresses("a@example.com"), ["a@example.com"])

    def test_list_returned_as_list(self):
        addrs = ["a@example.com", "b@example.com"]
        self.assertEqual(_normalize_addresses(addrs), addrs)


class TestBuildMessage(unittest.TestCase):
    def test_basic_message(self):
        msg = build_message(
            sender="sender@example.com",
            to_list=["recipient@example.com"],
            subject="Hello",
            body="World",
        )
        self.assertEqual(msg["From"], "sender@example.com")
        self.assertEqual(msg["To"], "recipient@example.com")
        self.assertEqual(msg["Subject"], "Hello")
        self.assertIsNone(msg["Cc"])

    def test_cc_header_set(self):
        msg = build_message(
            sender="sender@example.com",
            to_list=["recipient@example.com"],
            subject="Hello",
            body="World",
            cc_list=["cc1@example.com", "cc2@example.com"],
        )
        self.assertEqual(msg["Cc"], "cc1@example.com, cc2@example.com")

    def test_multiple_recipients(self):
        msg = build_message(
            sender="sender@example.com",
            to_list=["a@example.com", "b@example.com"],
            subject="Test",
            body="Body",
        )
        self.assertEqual(msg["To"], "a@example.com, b@example.com")

    def test_empty_cc_list_no_header(self):
        msg = build_message(
            sender="sender@example.com",
            to_list=["recipient@example.com"],
            subject="Test",
            body="Body",
            cc_list=[],
        )
        self.assertIsNone(msg["Cc"])

    def test_plain_text_only_no_alternative_part(self):
        msg = build_message(
            sender="sender@example.com",
            to_list=["recipient@example.com"],
            subject="Plain",
            body="Hello plain",
        )
        payloads = msg.get_payload()
        self.assertEqual(len(payloads), 1)
        self.assertEqual(payloads[0].get_content_type(), "text/plain")
        self.assertEqual(payloads[0].get_payload(), "Hello plain")

    def test_html_body_creates_alternative_part(self):
        msg = build_message(
            sender="sender@example.com",
            to_list=["recipient@example.com"],
            subject="HTML",
            body="Hello plain",
            html_body="<p>Hello <b>HTML</b></p>",
        )
        payloads = msg.get_payload()
        self.assertEqual(len(payloads), 1)
        alternative = payloads[0]
        self.assertEqual(alternative.get_content_type(), "multipart/alternative")
        parts = alternative.get_payload()
        self.assertEqual(len(parts), 2)
        plain_part, html_part = parts
        self.assertEqual(plain_part.get_content_type(), "text/plain")
        self.assertEqual(html_part.get_content_type(), "text/html")

    def test_html_body_content(self):
        html = "<h1>Title</h1><p>Body</p>"
        msg = build_message(
            sender="sender@example.com",
            to_list=["recipient@example.com"],
            subject="HTML Content",
            body="Title\nBody",
            html_body=html,
        )
        alternative = msg.get_payload()[0]
        plain_part, html_part = alternative.get_payload()
        self.assertEqual(plain_part.get_payload(), "Title\nBody")
        self.assertIn("<h1>Title</h1>", html_part.get_payload())

    def test_html_body_with_cc(self):
        msg = build_message(
            sender="sender@example.com",
            to_list=["recipient@example.com"],
            subject="HTML CC",
            body="Plain",
            cc_list=["cc@example.com"],
            html_body="<p>HTML</p>",
        )
        self.assertEqual(msg["Cc"], "cc@example.com")
        alternative = msg.get_payload()[0]
        self.assertEqual(alternative.get_content_type(), "multipart/alternative")


class TestSendEmail(unittest.TestCase):
    @patch("email_service.smtplib.SMTP")
    def test_send_basic_email(self, mock_smtp_cls):
        mock_server = MagicMock()
        mock_smtp_cls.return_value.__enter__ = MagicMock(return_value=mock_server)
        mock_smtp_cls.return_value.__exit__ = MagicMock(return_value=False)

        send_email(
            smtp_host="smtp.example.com",
            smtp_port=587,
            sender="sender@example.com",
            recipients="to@example.com",
            subject="Hi",
            body="Hello",
            use_tls=False,
        )

        mock_smtp_cls.assert_called_once_with("smtp.example.com", 587)
        mock_server.sendmail.assert_called_once()
        _, recipients_arg, _ = mock_server.sendmail.call_args[0]
        self.assertIn("to@example.com", recipients_arg)

    @patch("email_service.smtplib.SMTP")
    def test_cc_recipients_included_in_sendmail(self, mock_smtp_cls):
        mock_server = MagicMock()
        mock_smtp_cls.return_value.__enter__ = MagicMock(return_value=mock_server)
        mock_smtp_cls.return_value.__exit__ = MagicMock(return_value=False)

        send_email(
            smtp_host="smtp.example.com",
            smtp_port=587,
            sender="sender@example.com",
            recipients="to@example.com",
            subject="Hi",
            body="Hello",
            cc="cc@example.com",
            use_tls=False,
        )

        _, recipients_arg, _ = mock_server.sendmail.call_args[0]
        self.assertIn("cc@example.com", recipients_arg)

    @patch("email_service.smtplib.SMTP")
    def test_duplicate_addresses_deduplicated(self, mock_smtp_cls):
        mock_server = MagicMock()
        mock_smtp_cls.return_value.__enter__ = MagicMock(return_value=mock_server)
        mock_smtp_cls.return_value.__exit__ = MagicMock(return_value=False)

        send_email(
            smtp_host="smtp.example.com",
            smtp_port=587,
            sender="sender@example.com",
            recipients="shared@example.com",
            subject="Hi",
            body="Hello",
            cc="shared@example.com",
            use_tls=False,
        )

        _, recipients_arg, _ = mock_server.sendmail.call_args[0]
        self.assertEqual(recipients_arg.count("shared@example.com"), 1)

    @patch("email_service.smtplib.SMTP")
    def test_tls_and_auth(self, mock_smtp_cls):
        mock_server = MagicMock()
        mock_smtp_cls.return_value.__enter__ = MagicMock(return_value=mock_server)
        mock_smtp_cls.return_value.__exit__ = MagicMock(return_value=False)

        send_email(
            smtp_host="smtp.example.com",
            smtp_port=587,
            sender="sender@example.com",
            recipients="to@example.com",
            subject="Hi",
            body="Hello",
            username="user",
            password="pass",
            use_tls=True,
        )

        mock_server.starttls.assert_called_once()
        mock_server.login.assert_called_once_with("user", "pass")

    @patch("email_service.smtplib.SMTP")
    def test_smtp_exception_raises_runtime_error(self, mock_smtp_cls):
        import smtplib

        mock_server = MagicMock()
        mock_server.sendmail.side_effect = smtplib.SMTPException("connection refused")
        mock_smtp_cls.return_value.__enter__ = MagicMock(return_value=mock_server)
        mock_smtp_cls.return_value.__exit__ = MagicMock(return_value=False)

        with self.assertRaises(RuntimeError):
            send_email(
                smtp_host="smtp.example.com",
                smtp_port=587,
                sender="sender@example.com",
                recipients="to@example.com",
                subject="Hi",
                body="Hello",
                use_tls=False,
            )

    @patch("email_service.smtplib.SMTP")
    def test_send_html_email(self, mock_smtp_cls):
        mock_server = MagicMock()
        mock_smtp_cls.return_value.__enter__ = MagicMock(return_value=mock_server)
        mock_smtp_cls.return_value.__exit__ = MagicMock(return_value=False)

        send_email(
            smtp_host="smtp.example.com",
            smtp_port=587,
            sender="sender@example.com",
            recipients="to@example.com",
            subject="HTML Email",
            body="Hello plain",
            html_body="<p>Hello <b>HTML</b></p>",
            use_tls=False,
        )

        mock_server.sendmail.assert_called_once()
        _, recipients_arg, raw_msg = mock_server.sendmail.call_args[0]
        self.assertIn("to@example.com", recipients_arg)
        self.assertIn("multipart/alternative", raw_msg)
        self.assertIn("text/html", raw_msg)
        self.assertIn("text/plain", raw_msg)

    @patch("email_service.smtplib.SMTP")
    def test_send_html_email_with_cc(self, mock_smtp_cls):
        mock_server = MagicMock()
        mock_smtp_cls.return_value.__enter__ = MagicMock(return_value=mock_server)
        mock_smtp_cls.return_value.__exit__ = MagicMock(return_value=False)

        send_email(
            smtp_host="smtp.example.com",
            smtp_port=587,
            sender="sender@example.com",
            recipients="to@example.com",
            subject="HTML CC Email",
            body="Plain",
            cc="cc@example.com",
            html_body="<p>HTML</p>",
            use_tls=False,
        )

        _, recipients_arg, raw_msg = mock_server.sendmail.call_args[0]
        self.assertIn("cc@example.com", recipients_arg)
        self.assertIn("multipart/alternative", raw_msg)


if __name__ == "__main__":
    unittest.main()
