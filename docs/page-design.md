# The Daily Brief — Page Design

## Page Layout

One scrollable page, top to bottom:

```
┌──────────────────────────────────────────────────┐
│  THE DAILY BRIEF          Friday, Sep 12 · #42   │  ← masthead
├──────────────────────────────────────────────────┤
│  "Your morning looks loaded."                    │  ← AI headline
│  Reply to Alex, close PR #88 before standup.    │  ← AI recommendation
├──────────────────────────────────────────────────┤
│  ACTION REQUIRED                                 │
│  ┌─────────────────────────────────────────────┐ │
│  │ [gmail · work]  Contract review from Alex   │ │
│  │ [gmail]         Invoice from Stripe         │ │
│  │ [slack]         Mention in #backend         │ │
│  └─────────────────────────────────────────────┘ │
├──────────────────────────────────────────────────┤
│  MISSED OVERNIGHT                                │
│  ┌─────────────────────────────────────────────┐ │
│  │ [gmail · work]  3 emails from team          │ │
│  │ [telegram]      Message from Maria          │ │
│  └─────────────────────────────────────────────┘ │
├──────────────────────────────────────────────────┤
│  TODAY'S SCHEDULE                                │
│  ┌─────────────────────────────────────────────┐ │
│  │ 10:00  [calendar]  Standup                  │ │
│  │ 14:00  [calendar]  Design review            │ │
│  │ All clear ✓  (if no events)                 │ │
│  └─────────────────────────────────────────────┘ │
├──────────────────────────────────────────────────┤
│  TASKS & GOALS                                   │
│  ┌─────────────────────────────────────────────┐ │
│  │ [obsidian]  Finish architecture doc         │ │
│  │ [obsidian]  Review PR before EOD            │ │
│  └─────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────┘
```

---

## Sections

Fixed order, always rendered:

| # | Section | Content |
|---|---------|---------|
| 1 | **Action Required** | Unanswered emails, urgent tasks, mentions |
| 2 | **Missed Overnight** | Emails, messages, events received while sleeping |
| 3 | **Today's Schedule** | Calendar events sorted by time |
| 4 | **Tasks & Goals** | Open Obsidian TODOs and projects |

Empty section → always shown with **"All clear ✓"** message, never hidden.

---

## Source Tags

Each item shows where it came from as a small muted text badge:

- `[gmail]` — personal Gmail
- `[gmail · work]` — work Gmail account
- `[obsidian]` — Obsidian vault
- `[calendar]` — Google Calendar
- `[telegram]` — Telegram
- `[slack]` — Slack

Tag style: small, gray, no heavy styling — just enough to know the source at a glance.

---

## Item Structure

```
[source tag]  Title of the item
              Short summary (1–2 lines, written by LLM)
              → Deep link
```

- LLM decides priority order within each section (most urgent first)
- Urgent items get a red accent badge (`#c92a2a`) — the only color on the page
- Everything else: black on white

---

## Visual Style

- **Theme**: Light, clean, newspaper editorial
- **Typography**: Playfair Display (masthead + section headers) · Inter (body)
- **Layout**: Single column, full-width sections, scroll
- **Accent**: `#c92a2a` red for urgent items only
- **Source badge**: small muted gray inline tag

---

## Multiple Accounts (e.g. work Gmail)

User defines account aliases in `config.yaml`:

```yaml
connectors:
  gmail:
    enabled: true
    label: personal           # shown as [gmail]

  gmail_work:
    enabled: true
    label: gmail · work       # shown as [gmail · work]
```

Items from both accounts flow into the same sections — distinguished by their tag only.
No page splitting. No separate columns.

---

## Secrets & API Keys

- All API keys live in `.env` at `~/.the-daily-brief/.env`
- Never in `config.yaml`
- `.env` is gitignored
- Local script → `.env` is the right and only approach, no need to overcomplicate

---

## Future: Setup CLI

`tdbrief setup` — interactive wizard (Phase 3+):
- Add connector, give it a label
- Enter API key (saved to `.env`)
- Enable / disable

Inspired by Vue CLI / OpenAI CLI. Not MVP.
