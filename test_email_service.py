"""
Tests for the email service CC functionality.
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


class TestSendEmail(unittest.TestCase):
    def _make_mock_smtp(self):
        mock_server = MagicMock()
        mock_smtp_cls = MagicMock()
        mock_smtp_cls.return_value.__enter__ = MagicMock(return_value=mock_server)
        mock_smtp_cls.return_value.__exit__ = MagicMock(return_value=False)
        return mock_smtp_cls, mock_server

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


if __name__ == "__main__":
    unittest.main()
