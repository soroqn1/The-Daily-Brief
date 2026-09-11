# The Daily Brief — Roadmap

## Phase 1 — MVP

> Goal: wake up, open laptop, brief appears in browser.

- [x] Project scaffold (`uv`, `pyproject.toml`, `Taskfile.yml`)
- [x] `config.yaml` + `.env` loading (`config.py`)
- [x] `state.py` — track last brief date, enforce 09:00 cutoff
- [x] `BaseConnector` ABC — `fetch() -> list[BriefItem]`
- [x] `connectors/gmail.py` — unread & flagged emails via Gmail API (OAuth)
- [x] `connectors/obsidian.py` — open TODOs, incomplete tasks from vault markdown
- [ ] `BaseLLMClient` ABC — unified interface for LLM providers
- [ ] `llm/gemini.py` — Gemini API client
- [ ] `llm/openai.py` — OpenAI GPT-4o client
- [ ] `renderer/renderer.py` — `BriefData` (JSON) → HTML via Jinja2
- [ ] `renderer/templates/brief.html.j2` — newspaper-style light theme
- [ ] `notifier.py` — macOS notifications via `osascript`
- [ ] `main.py` — async orchestrator: gather → LLM → render → open → cleanup
- [ ] `trigger/com.dailybrief.plist` — launchd LaunchAgent (wake-from-sleep)
- [ ] Error handling: connector failure → skip + warn in brief; LLM failure → macOS alert

---

## Phase 2 — Calendar & Messaging

- [ ] `connectors/calendar.py` — Google Calendar: today's events, upcoming deadlines
- [ ] `connectors/telegram.py` — unread messages from priority chats
- [ ] Brief section: **Schedule** (time-sorted events for the day)
- [ ] Brief section: **Messages** (unanswered Telegram threads)

---

## Phase 3 — Extended Sources

- [ ] `connectors/slack.py` — unread mentions and DMs
- [ ] `connectors/imap.py` — generic IMAP connector (work email, any mailbox)
- [ ] `connectors/github.py` — assigned PRs, pending reviews, CI failures
- [ ] Multi-account Gmail support

---

## Future

- [ ] Weekly AI rollup — every Sunday, summarise the week's briefs
- [ ] In-browser archive — browse past briefs at `localhost` (FastAPI, optional)
- [ ] Anthropic Claude adapter
- [ ] Local LLM adapter (Ollama)
- [ ] Brief diff — highlight what changed since yesterday

---

## Principles (for every task)

- One connector = one file, implements `BaseConnector`, registered in `config.yaml`
- New LLM = one file, implements `BaseLLMClient`, selected via `config.yaml`
- Never raise inside a connector — log + return `[]`
- Zero speculative code — only what the current phase requires
- `task pre-commit` must pass before any commit (`ruff` lint + format)
