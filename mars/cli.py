"""MARS command line.

Examples:
    python -m mars.cli import-export chat.txt --owner "Romano Silva" --chat "Jane Doe"
    python -m mars.cli contacts
    python -m mars.cli analytics
    python -m mars.cli followups --min-age-hours 12
    python -m mars.cli summary "Jane"
    python -m mars.cli prep "Jane"
"""

from __future__ import annotations

import argparse
import sys
from collections import defaultdict

from .config import Config
from .db import Store
from .ingest.export_parser import parse_export
from .ingest.msgstore import parse_msgstore
from .analysis import analytics, crm, meeting_prep, summaries


def _store(config: Config) -> Store:
    return Store(config.db_path)


def _names(store: Store) -> dict[str, str]:
    return {c.wa_id: (c.display_name or c.wa_id) for c in store.contacts()}


def _per_chat(store: Store):
    per = defaultdict(list)
    for m in store.all_messages():
        per[m.chat_id].append(m)
    return per


def cmd_import_export(args, config: Config) -> int:
    with open(args.file, encoding="utf-8") as fh:
        text = fh.read()
    chat_id = args.chat or args.file
    msgs = parse_export(
        text, owner_name=args.owner, chat_id=chat_id,
        dayfirst=not args.monthfirst, include_system=args.system,
    )
    store = _store(config)
    # Register the contact under the chat id using the most common inbound sender.
    inbound_names = [m.sender_id for m in msgs if m.direction == "in"]
    display = max(set(inbound_names), key=inbound_names.count) if inbound_names else chat_id
    if msgs:
        store.upsert_contact(chat_id, display, min(m.ts for m in msgs))
        store.upsert_contact(chat_id, display, max(m.ts for m in msgs))
    added = store.add_messages(msgs)
    print(f"Parsed {len(msgs)} messages from {args.file}; stored {added} new "
          f"under chat '{chat_id}' (contact: {display}).")
    return 0


def cmd_import_msgstore(args, config: Config) -> int:
    parsed = parse_msgstore(args.file)
    store = _store(config)
    for chat_id, name in parsed.names.items():
        if parsed.messages:
            store.upsert_contact(chat_id, name, 0)
    # Track first/last seen from the messages themselves.
    spans: dict[str, list[int]] = {}
    for m in parsed.messages:
        spans.setdefault(m.chat_id, [m.ts, m.ts])
        spans[m.chat_id][0] = min(spans[m.chat_id][0], m.ts)
        spans[m.chat_id][1] = max(spans[m.chat_id][1], m.ts)
    for chat_id, (first, last) in spans.items():
        store.upsert_contact(chat_id, parsed.names.get(chat_id, chat_id), first)
        store.upsert_contact(chat_id, parsed.names.get(chat_id, chat_id), last)
    added = store.add_messages(parsed.messages)
    print(f"Parsed {len(parsed.messages)} messages across "
          f"{len(parsed.names)} chats from {args.file}; stored {added} new.")
    return 0


def cmd_contacts(args, config: Config) -> int:
    store = _store(config)
    rows = store.contacts()
    if not rows:
        print("No contacts yet. Import an export or run the webhook ingest.")
        return 0
    print(f"{'contact':<30}{'chat_id':<22}{'messages':>9}")
    counts = analytics.compute(store.all_messages()).by_contact
    for c in rows:
        print(f"{(c.display_name or c.wa_id):<30}{c.wa_id:<22}{counts.get(c.wa_id, 0):>9}")
    return 0


def cmd_analytics(args, config: Config) -> int:
    store = _store(config)
    a = analytics.compute(store.all_messages())
    names = _names(store)
    print(analytics.render(a, name_of=lambda cid: names.get(cid, cid)))
    return 0


def cmd_followups(args, config: Config) -> int:
    store = _store(config)
    states = crm.thread_states(_per_chat(store), _names(store))
    print(crm.render_followups(states, min_age_secs=args.min_age_hours * 3600))
    return 0


def _resolve(store: Store, needle: str):
    c = store.find_contact(needle)
    if c is None:
        print(f"No contact matching '{needle}'.", file=sys.stderr)
        return None
    return c


def cmd_summary(args, config: Config) -> int:
    store = _store(config)
    c = _resolve(store, args.contact)
    if c is None:
        return 1
    msgs = store.messages_for_chat(c.wa_id)
    print(summaries.summarize(config, c.display_name or c.wa_id, msgs))
    return 0


def cmd_prep(args, config: Config) -> int:
    store = _store(config)
    c = _resolve(store, args.contact)
    if c is None:
        return 1
    msgs = store.messages_for_chat(c.wa_id)
    print(meeting_prep.brief(config, c.display_name or c.wa_id, msgs))
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="mars", description="WhatsApp analysis & CRM")
    sub = p.add_subparsers(dest="cmd", required=True)

    ie = sub.add_parser("import-export", help="ingest a WhatsApp Export Chat .txt")
    ie.add_argument("file")
    ie.add_argument("--owner", required=True,
                    help="the sender label that represents YOU in the export")
    ie.add_argument("--chat", help="chat id/name (defaults to filename)")
    ie.add_argument("--monthfirst", action="store_true",
                    help="dates are M/D/Y instead of D/M/Y")
    ie.add_argument("--system", action="store_true",
                    help="keep system notices")
    ie.set_defaults(func=cmd_import_export)

    ms = sub.add_parser("import-msgstore",
                        help="ingest a decrypted WhatsApp msgstore.db")
    ms.add_argument("file")
    ms.set_defaults(func=cmd_import_msgstore)

    sub.add_parser("contacts", help="list known contacts").set_defaults(
        func=cmd_contacts)
    sub.add_parser("analytics", help="patterns & analytics").set_defaults(
        func=cmd_analytics)

    fu = sub.add_parser("followups", help="who you owe replies to")
    fu.add_argument("--min-age-hours", type=int, default=0)
    fu.set_defaults(func=cmd_followups)

    sm = sub.add_parser("summary", help="per-person summary")
    sm.add_argument("contact")
    sm.set_defaults(func=cmd_summary)

    pr = sub.add_parser("prep", help="meeting prep for a contact")
    pr.add_argument("contact")
    pr.set_defaults(func=cmd_prep)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args, Config.from_env())


if __name__ == "__main__":
    raise SystemExit(main())
