import services.email_service as email_service


def test_invite_email_uses_resend_without_real_network(monkeypatch):
    sent = {}

    class FakeEmails:
        @staticmethod
        def send(payload):
            sent.update(payload)

    monkeypatch.delenv("EMAIL_USER", raising=False)
    monkeypatch.delenv("EMAIL_PASS", raising=False)
    monkeypatch.setenv("RESEND_API_KEY", "offline-test-key")
    monkeypatch.setattr(email_service.resend, "Emails", FakeEmails)

    result = email_service.send_email(
        "invitee@example.test",
        "DataSpeakAI invitation",
        "Use the invitation link.",
        "<p>Use the invitation link.</p>",
    )

    assert result is True
    assert sent["to"] == "invitee@example.test"
    assert "invitation" in sent["subject"].lower()


def test_invite_email_reports_unconfigured_provider(monkeypatch):
    monkeypatch.delenv("EMAIL_USER", raising=False)
    monkeypatch.delenv("EMAIL_PASS", raising=False)
    monkeypatch.delenv("RESEND_API_KEY", raising=False)

    assert email_service.send_email("invitee@example.test", "Subject", "Body") is False
