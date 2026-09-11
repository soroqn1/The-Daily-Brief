# The Daily Brief — Vision

> *"Every morning, your newspaper is already printed."*

## What is it?

**The Daily Brief** is a personal morning intelligence system.
Every time you open your laptop, it wakes up, scans your connected sources, feeds the data to an LLM, and renders a clean HTML newspaper — already waiting in your browser.

No app. No login. No noise. Just your day, curated.

---

## Core Idea

You wake up. MacBook wakes up. Within seconds, a beautiful HTML page opens in your browser with:

- What happened while you slept (missed emails, events, deadlines)
- What needs your attention today (unanswered messages, tasks)
- Your schedule for the day (meetings, calls, deadlines)
- Open items from Obsidian (unfinished TODOs, stalled projects)
- AI recommendation: *"Reply to X, close Y, don't miss Z"*

Each brief is saved as an HTML file (rolling 7-day archive, then auto-deleted).

---

## Design Philosophy

| Principle | Description |
|-----------|-------------|
| **Plug & play sources** | Add/remove data sources from one config file — no digging through code |
| **LLM-powered** | Raw data → LLM → structured, readable brief in Russian |
| **Zero noise** | Only actionable information. No stats for stats' sake |
| **Gazette aesthetic** | Light, clean, newspaper typography |
| **Wake-trigger** | Fires on Mac wake-from-sleep, not on a clock schedule |
| **Local-first** | Runs 100% on your machine, no cloud dependency |
| **Extensible** | Each source is an independent connector; swap LLMs in config |

---

## Visual Style

- **Theme**: Light, clean, newspaper / editorial
- **Typography**: Serif headline font + clean sans-serif body
- **Layout**: Column-based, structured like a morning paper front page
- **Color**: Minimal — ink on white, accent color for "urgent" items only

---

## Data Sources — Roadmap

Sources are loaded as **connectors** — independent modules with a standard interface.

### MVP (Phase 1)
- **Gmail** — unread & important emails since last brief
- **Obsidian** — open TODOs, incomplete projects, daily note

### Phase 2
- **Google Calendar** — today's schedule, upcoming deadlines
- **Telegram** — unanswered messages from key chats

### Phase 3
- **Slack / Discord** — workspace messages
- **Additional email** (work mailboxes via IMAP)
- **GitHub** — assigned PRs, reviews pending

### Future
- **Weekly summary** — AI rollup of the week's briefs (every Sunday)
- **Historical archive UI** — browse past briefs in browser

---

## Trigger Mechanism

| Event | Action |
|-------|--------|
| MacBook wakes from sleep | `launchd` fires the brief generator script |
| Script runs | Fetches data from all active connectors |
| LLM processes | Structured brief is generated |
| Browser opens | Latest brief HTML displayed automatically |

Implementation: macOS **LaunchAgent** (`plist`) listening for system wake event.

---

## LLM Strategy

- **MVP**: Gemini API + OpenAI GPT-4o (configurable per preference)
- **Future**: any LLM via unified adapter (Anthropic, local Ollama)
- **Prompt**: Structured JSON payload → LLM → editorial English text
- **Cost**: Email summarization is lightweight; not expensive at daily frequency

---

## Storage

```
~/.the-daily-brief/          # default, user-configurable
  briefs/
    2026-09-12.html
    2026-09-11.html
    ...                  # auto-deleted after 7 days
  config.yaml            # all settings, connectors, tokens
  connectors/            # pluggable source modules
```

---

## What This Is NOT

- Not a web app (no hosting, no SaaS)
- Not a mobile app
- Not a dashboard you keep open all day
- Not a task manager — it reads from your tools, doesn't replace them
