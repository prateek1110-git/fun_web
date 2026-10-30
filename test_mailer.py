import unittest

from mailer import Mailer, booking_message, format_slot


class FakeSMTP:
    instances = []
    fail = False

    def __init__(self, host, port, timeout=None):
        self.host, self.port = host, port
        self.calls = []
        self.sent = []
        FakeSMTP.instances.append(self)

    def __enter__(self):
        if FakeSMTP.fail:
            raise OSError("connection refused")
        return self

    def __exit__(self, *exc):
        return False

    def starttls(self):
        self.calls.append("starttls")

    def login(self, user, password):
        self.calls.append(("login", user, password))

    def send_message(self, message):
        self.sent.append(message)


def make_mailer(port=587, **overrides):
    args = dict(host="smtp.test", port=port, username="u", password="p", sender="from@x.com", recipient="to@x.com")
    args.update(overrides)
    return Mailer(smtp_class=FakeSMTP, **args)


class FormatTest(unittest.TestCase):
    def test_format_slot(self):
        self.assertEqual(format_slot("2026-11-02T10"), "Monday, 2 Nov 2026, 10 AM – 11 AM")
        self.assertEqual(format_slot("2026-11-02T23"), "Monday, 2 Nov 2026, 11 PM – 12 AM")
        self.assertEqual(format_slot("2026-11-02T12"), "Monday, 2 Nov 2026, 12 PM – 1 PM")

    def test_booking_message_keeps_user_text_out_of_subject(self):
        subject, body = booking_message("Ritika", "2026-11-02T10", "Chai\nBcc: evil@x.com", "hello")
        self.assertEqual(subject, "📅 Ritika booked time with you")
        self.assertIn("Reason: Chai\nBcc: evil@x.com", body)
        self.assertIn("Note:   hello", body)

    def test_booking_message_omits_empty_note(self):
        self.assertNotIn("Note:", booking_message("Ritika", "2026-11-02T10", "Chai", "")[1])


class MailerTest(unittest.TestCase):
    def setUp(self):
        FakeSMTP.instances.clear()
        FakeSMTP.fail = False

    def test_send_uses_starttls_login_and_addresses(self):
        make_mailer().send("Subj", "Body")
        smtp = FakeSMTP.instances[0]
        self.assertEqual(smtp.calls, ["starttls", ("login", "u", "p")])
        message = smtp.sent[0]
        self.assertEqual((message["To"], message["From"], message["Subject"]), ("to@x.com", "from@x.com", "Subj"))

    def test_ssl_port_skips_starttls(self):
        make_mailer(port=465).send("Subj", "Body")
        self.assertEqual(FakeSMTP.instances[0].calls, [("login", "u", "p")])

    def test_no_login_without_username(self):
        make_mailer(username="").send("Subj", "Body")
        self.assertEqual(FakeSMTP.instances[0].calls, ["starttls"])

    def test_from_env_disabled_when_unconfigured(self):
        self.assertFalse(Mailer.from_env({}).enabled)
        self.assertFalse(Mailer.from_env({"SMTP_HOST": "h"}).enabled)
        self.assertIsNone(Mailer.from_env({}).send_async("s", "b"))

    def test_from_env_enabled_and_sender_defaults_to_user(self):
        mailer = Mailer.from_env({"SMTP_HOST": "h", "NOTIFY_EMAIL": "to@x.com", "SMTP_USER": "me@x.com"})
        self.assertTrue(mailer.enabled)
        self.assertEqual(mailer._sender, "me@x.com")
        self.assertEqual(mailer._port, 587)

    def test_send_async_swallows_errors(self):
        FakeSMTP.fail = True
        make_mailer().send_async("s", "b").join(2)

    def test_send_async_delivers(self):
        make_mailer().send_async("s", "b").join(2)
        self.assertEqual(len(FakeSMTP.instances[0].sent), 1)


if __name__ == "__main__":
    unittest.main()
