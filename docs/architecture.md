# The Daily Brief — Architecture

## System Overview

```
[Browser Startpage / Custom Tab / CLI]
        │
        ▼ GET/POST /{space}/daily or /{space}/email
[FastAPI Server / main.py orchestrator]
        │
        ├─── [connector: gmail (space token)] ─┐
        ├─── [connector: obsidian (dirs)]     ─┤ → List[BriefItem] (async, parallel)
        └─── [connector: ...]                 ─┘
                                                │
                                                ▼
                                        [LLM client]
                                structured JSON input (daily or email audit)
                                                │
                                                ▼ JSON response
                                        [renderer / Jinja2]
                                                │
                                                ▼ saves .md + .html
                        ~/Desktop/TheDailyBrief/<DD-MM-YY>/<space>/
                        ├── daily.md & daily.html
                        └── email.md & email.html
                                                │
                                                ▼
                        [Browser View with "Copy Path for AI" Button]
```

---

## Repository Structure

```
the-daily-brief/
├── the_daily_brief/
│   ├── __init__.py
│   ├── main.py              # entry point, orchestrator & CLI
│   ├── server.py            # local FastAPI web server
│   ├── config.py            # loads config.yaml + .env + spaces
│   ├── state.py             # read/write ~/.the-daily-brief/state.json
│   ├── models.py            # BriefData, BriefItem, EmailAuditData
│   ├── auth.py              # interactive Google OAuth helper (--space support)
│   ├── connectors/
│   │   ├── base.py          # BaseConnector ABC → fetch() → List[BriefItem]
│   │   ├── registry.py      # dynamic connector registry, setup guides & factories
│   │   ├── gmail.py         # Gmail connector (supports spaces & fetch_audit)
│   │   └── obsidian.py
│   ├── llm/
│   │   ├── base.py          # BaseLLMClient ABC
│   │   ├── gemini.py        # Gemini daily & email audit generation
│   │   └── openai.py        # OpenAI daily & email audit generation
│   ├── renderer/
│   │   ├── renderer.py      # BriefData / EmailAuditData → HTML + Markdown
│   │   └── templates/
│   │       ├── brief.html.j2
│   │       ├── email_audit.html.j2
│   │       └── global_feed.html.j2
│   └── notifier.py          # macOS osascript notifications
├── config.yaml              # user-facing config & spaces
├── pyproject.toml           # uv / PEP 517
├── Taskfile.yml
└── docs/
    ├── vision.md
    └── architecture.md
```

---

## Report Modes

### 1. Daily Brief (`/{space}/daily`)
- Comprehensive overview across connected sources:
  - `action_required`: urgent messages, unanswered emails, invoices
  - `missed`: messages received overnight or while away
  - `schedule`: upcoming events
  - `tasks`: open tasks and project TODOs from Obsidian
  - `ai_recommendation`: editorial guidance on what to prioritize

### 2. Email Audit (`/{space}/email`)
- Deep inbox audit over the last 3–7 days (configurable via `audit_days`):
  - `needs_reply`: emails awaiting a response from the user
  - `commitments_and_pending`: promises made, in-flight agreements
  - `deadlines_and_urgent`: deadlines, expiring links, bills
  - `checklist`: actionable checklist of tasks to complete or people to reply to

---

## Storage & Saves

Reports are saved to `storage_dir` (configurable via `DAILY_BRIEF_STORAGE_PATH` in `.env` or `storage_dir` in `config.yaml`, defaulting to `~/Desktop/TheDailyBrief`):

```
~/Desktop/TheDailyBrief/
└── 20-09-26/                 # DD-MM-YY
    ├── work/
    │   ├── daily.md          # Clean text formatted for Claude / Hermes / AI agents
    │   ├── daily.html        # Styled web view with "Copy Path for AI" button
    │   ├── email.md
    │   └── email.html
    └── study/
        ├── daily.md
        └── ...
```

---

## Web Endpoints (FastAPI)

- `GET /` or `GET /settings` — Local Hub dashboard with spaces, connects, and interactive modals
- `GET /global/daily` — Unified Reddit-style daily feed across all spaces
- `POST /global/daily` — Force regenerate unified global feed
- `GET /global/daily/raw` — Fetch raw Markdown of unified global feed
- `GET /{space}/daily` — Display or generate today's daily brief in HTML
- `POST /{space}/daily` — Force regenerate daily brief (returns JSON with paths)
- `GET /{space}/daily/raw` — Fetch raw Markdown of daily brief
- `GET /{space}/email` — Display or generate today's email audit in HTML
- `POST /{space}/email` — Force regenerate email audit (returns JSON with paths)
- `GET /{space}/email/raw` — Fetch raw Markdown of email audit
- `GET /api/connector-types` — List available connector types with setup guides and fields
- `GET /api/spaces` — List configured spaces and their connectors
- `POST /api/spaces` — Create a new space
- `DELETE /api/spaces/{space}` — Delete a space
- `POST /api/spaces/{space}/connectors` — Add/update connector in a space
- `DELETE /api/spaces/{space}/connectors/{conn_id}` — Remove connector from space
