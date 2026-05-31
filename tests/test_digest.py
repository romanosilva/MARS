from mars.analysis import digest
from mars.analysis.crm import ThreadState
from mars.config import Config
from mars.models import INBOUND, OUTBOUND
from mars.notify import email_out

HOUR = 3600
DAY = 86400
NOW = 100 * DAY


def _state(name, last_ts, awaiting, snippet="hi"):
    return ThreadState(
        chat_id=name, name=name, last_ts=last_ts,
        last_direction=INBOUND if awaiting else OUTBOUND,
        last_snippet=snippet, awaiting_you=awaiting,
        age_secs=max(0, NOW - last_ts))


def test_digest_counts_and_subject():
    states = [
        _state("Jane", NOW - 3 * DAY, True, "any update?"),   # stale (red)
        _state("Bob", NOW - 2 * HOUR, True, "free today?"),   # fresh
        _state("Carol", NOW - 5 * DAY, False, "thanks!"),     # waiting on them
    ]
    subject, body = digest.build(states, now=NOW)
    assert "2 replies owed" in subject
    assert "aging past 48h" in body          # Jane triggers the stale note
    assert "Jane" in body and "Bob" in body
    assert "Waiting on them (1)" in body
    assert "Carol" in body


def test_digest_inbox_zero():
    states = [_state("Carol", NOW - DAY, False)]
    subject, body = digest.build(states, now=NOW)
    assert "0 replies owed" in subject
    assert "Inbox zero" in body


def test_owe_min_filter():
    states = [_state("Bob", NOW - 2 * HOUR, True)]
    subject, _ = digest.build(states, now=NOW, owe_min_secs=12 * HOUR)
    assert "0 replies owed" in subject       # Bob too recent to include


def _cfg(**over):
    base = dict(
        db_path=":memory:", verify_token="", app_secret="", access_token="",
        phone_number_id="", anthropic_api_key="", summary_model="m",
        smtp_host="smtp.example.com", smtp_port=587, smtp_user="me@example.com",
        smtp_password="pw", smtp_from="me@example.com", smtp_to="me@example.com",
        smtp_starttls=True)
    base.update(over)
    return Config(**base)


def test_email_message_headers():
    cfg = _cfg()
    msg = email_out.build_message(cfg, "subj", "body text")
    assert msg["To"] == "me@example.com"
    assert msg["Subject"] == "subj"
    assert msg.get_content().strip() == "body text"


def test_smtp_configured_flag():
    assert _cfg().smtp_configured is True
    assert _cfg(smtp_to="").smtp_configured is False
