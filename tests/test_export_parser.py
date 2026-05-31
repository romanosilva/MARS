from mars.ingest.export_parser import parse_export, parse_raw
from mars.models import INBOUND, OUTBOUND

IOS = """[2024/01/15, 09:30:00] Jane Doe: Hi professor, quick question
[2024/01/15, 09:30:10] Jane Doe: about the assignment
[2024/01/15, 11:00:00] Romano Silva: Sure, go ahead
this is a second line
[2024/01/15, 11:05:00] Jane Doe: ‎image omitted
"""

ANDROID = """15/01/2024, 09:30 - Messages are end-to-end encrypted.
15/01/2024, 09:31 - Jane Doe: Hello there
15/01/2024, 10:00 - Romano Silva: Hi Jane
"""


def test_ios_format_directions_and_multiline():
    msgs = parse_export(IOS, owner_name="Romano Silva", chat_id="jane")
    assert len(msgs) == 4
    assert msgs[0].direction == INBOUND
    assert msgs[2].direction == OUTBOUND
    # multi-line continuation got appended
    assert "second line" in msgs[2].body
    # media placeholder typed as media
    assert msgs[3].msg_type == "media"


def test_android_system_line_skipped_by_default():
    msgs = parse_export(ANDROID, owner_name="Romano Silva", chat_id="jane")
    assert len(msgs) == 2  # encryption notice skipped
    assert msgs[0].sender_id == "Jane Doe"
    assert msgs[1].direction == OUTBOUND


def test_system_line_kept_when_requested():
    msgs = parse_export(ANDROID, owner_name="Romano Silva", chat_id="jane",
                        include_system=True)
    assert msgs[0].msg_type == "system"


def test_timestamps_monotonic():
    raw = parse_raw(IOS)
    ts = [r.ts for r in raw]
    assert ts == sorted(ts)


def test_ids_are_stable():
    a = parse_export(IOS, owner_name="Romano Silva", chat_id="jane")
    b = parse_export(IOS, owner_name="Romano Silva", chat_id="jane")
    assert [m.msg_id for m in a] == [m.msg_id for m in b]
