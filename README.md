# MARS — Messaging Analysis & Relationship System

MARS ingests your WhatsApp conversations into a **local** store and turns them
into four things:

- **Patterns & analytics** — volume, reply ratios, your/their median response
  times, busiest hours and days, top contacts.
- **Per-person summaries** — topics, open asks, and your commitments per contact
  (with an optional LLM-written narrative).
- **Follow-up / CRM** — who you owe a reply to and how long it's been waiting.
- **Meeting prep** — an on-demand briefing before you talk to someone.

It reads data from two sources, both supported by a WhatsApp **Business**
account:

1. **Exported chat files** — full history of any conversation you export.
2. **Cloud API webhooks** — new messages, captured in real time going forward.

---

## What WhatsApp does and doesn't allow

This shapes the whole design, so it's worth stating plainly:

- There is **no API that dumps your past WhatsApp history**. Personal chats are
  end-to-end encrypted. Anything claiming to scrape them rides your logged-in
  session, violates WhatsApp's Terms, and risks a number ban. MARS does not do
  that.
- The **WhatsApp Business App** export (`Export Chat`) is the supported way to
  get *historical* data — it's a file you choose to produce.
- The **WhatsApp Business Platform / Cloud API** delivers *inbound* messages via
  webhook from the moment you set it up. It does not replay history and does not
  echo messages you send (only delivery statuses) — so outbound capture happens
  at send time.

In short: history comes from exports; the live feed comes from the Cloud API.

## Privacy note

The people in these chats — especially **students** — shared messages in
confidence. MARS keeps everything in a local SQLite file that is gitignored and
never leaves your machine. The only network call is the **optional** LLM summary,
and even then only the messages for the one contact you ask about are sent, and
only if you set `ANTHROPIC_API_KEY`. Consider telling contacts you keep records,
deleting the store when you no longer need it, and honoring any
institutional/FERPA-style obligations.

---

## Install

```bash
pip install -r requirements.txt        # anthropic is optional; rest is stdlib+fastapi
cp .env.example .env                    # fill in as needed
```

Nothing but `fastapi`/`uvicorn` (webhook) and `anthropic` (optional summaries) is
required — analytics, CRM, and heuristic prep run on the standard library.

## Source 1 — exported chats (history)

In the WhatsApp Business app: open a chat → **⋮ / contact name → Export Chat**
(with or without media). Then:

```bash
python -m mars.cli import-export jane.txt --owner "Your Name As It Appears" --chat "Jane Doe"
```

- `--owner` is the sender label that represents **you** in that export; those
  lines are stored as outbound.
- Add `--monthfirst` if your export uses M/D/Y dates.

## Source 1b — decrypted backup (bulk history)

If you'd rather not export each chat by hand, you can import a **decrypted**
`msgstore.db` in one shot:

```bash
python -m mars.cli import-msgstore msgstore.db
```

MARS does **not** decrypt backups and never touches your phone. You produce the
plain `msgstore.db` yourself from your own device (e.g. with `wa-crypt-tools`,
which needs the key from WhatsApp's app folder), then point MARS at it. Both the
legacy (`messages`) and modern (`message`/`chat`/`jid`) schemas are supported.
1:1 chats are keyed by phone number so they line up with Cloud API contacts;
group chats are keyed by their full jid. Display names live in a separate
`wa.db`, so contacts appear as phone numbers until you also have names.

## Source 2 — Cloud API (live feed)

1. Create a Meta app, add the **WhatsApp** product, register a phone number.
2. Set `WHATSAPP_VERIFY_TOKEN` (any string), `WHATSAPP_APP_SECRET`, and the
   token/phone-number id in `.env`.
3. Run the webhook and expose it over HTTPS:

   ```bash
   uvicorn mars.ingest.webhook:app --host 0.0.0.0 --port 8080
   ```

4. In the Meta app's WhatsApp → Configuration, set the callback URL to
   `https://<your-host>/webhook` and the same verify token, then subscribe to the
   `messages` field. Inbound messages now flow into the store automatically.

## Reports

```bash
python -m mars.cli contacts                 # list known contacts
python -m mars.cli analytics                # patterns & analytics
python -m mars.cli followups --min-age-hours 12
python -m mars.cli summary "Jane"           # per-person summary
python -m mars.cli prep "Jane"              # meeting prep briefing
```

`summary` and `prep` produce an LLM-written narrative when `ANTHROPIC_API_KEY`
is set, and fall back to a deterministic digest otherwise.

---

## Layout

```
mars/
  config.py              env-driven config
  db.py                  local SQLite store
  models.py              Message / Contact
  ingest/
    export_parser.py     WhatsApp 'Export Chat' .txt parser
    msgstore.py          decrypted msgstore.db importer (legacy + modern)
    cloud_api.py         webhook signature + payload parsing
    webhook.py           FastAPI ingest endpoint
  analysis/
    analytics.py         patterns & analytics
    crm.py               follow-up view
    heuristics.py        commitments / requests / open questions
    summaries.py         per-person summaries (+ optional LLM)
    meeting_prep.py      briefing (+ optional LLM)
    text.py              keyword extraction
    llm.py               optional Claude layer
  cli.py                 command line
tests/                   pytest suite
```

Run tests with `python -m pytest`.

## Status

Foundation: ingestion (both sources), storage, all four report types, tests.
Not yet built: group-chat participant modeling, outbound send + auto-logging via
the Cloud API, and a scheduled "daily follow-up digest". Open to prioritizing
any of these.
