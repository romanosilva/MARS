from mars.analysis import analytics, crm, heuristics
from mars.models import INBOUND, OUTBOUND, Message

HOUR = 3600


def _m(msg_id, chat, direction, ts, body=""):
    return Message(msg_id, chat, "x", direction, ts, "text", body, "test")


def _convo():
    # Jane asks at t0, you reply 1h later; Bob asks and you never reply.
    return [
        _m("1", "jane", INBOUND, 0, "can you review my thesis?"),
        _m("2", "jane", OUTBOUND, HOUR, "I'll send feedback by Friday"),
        _m("3", "bob", INBOUND, 2 * HOUR, "are you free tomorrow?"),
    ]


def test_counts_and_ratio():
    a = analytics.compute(_convo())
    assert a.total == 3
    assert a.inbound == 2 and a.outbound == 1
    assert a.by_contact["jane"] == 2


def test_reply_latency_measured():
    a = analytics.compute(_convo())
    assert a.your_reply_secs == [HOUR]


def test_followups_identifies_unanswered():
    per = {"jane": _convo()[:2], "bob": _convo()[2:]}
    states = crm.thread_states(per, {"jane": "Jane", "bob": "Bob"},
                               now=3 * HOUR)
    owe = {s.name: s for s in states if s.awaiting_you}
    assert "Bob" in owe        # last message inbound, unanswered
    assert "Jane" not in owe   # you replied last


def test_commitments_and_requests():
    msgs = _convo()
    commits = heuristics.commitments(msgs)
    asks = heuristics.open_requests(msgs)
    assert any("Friday" in m.body for m in commits)
    assert any("review" in m.body for m in asks)


def test_trailing_unanswered_run():
    msgs = [_m("1", "bob", OUTBOUND, 0), _m("2", "bob", INBOUND, HOUR, "ping?"),
            _m("3", "bob", INBOUND, 2 * HOUR, "still there?")]
    run = heuristics.trailing_unanswered(msgs)
    assert len(run) == 2
    assert run[-1].body == "still there?"
