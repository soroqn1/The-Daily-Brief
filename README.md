<div align="center">

  <img src="assets/banner.svg" alt="The Daily Brief Banner" width="100%" />

  <br/><br/>

  <p align="center">
    <strong>A bespoke newspaper-style morning brief on MacBook wake. Local-first, editorial, and 100% private.</strong>
  </p>

  <p align="center">
    <a href="https://python.org"><img src="https://img.shields.io/badge/Python-3.12%2B-blue?style=flat-square&logo=python&logoColor=white" alt="Python 3.12+" /></a>
    <a href="https://fastapi.tiangolo.com"><img src="https://img.shields.io/badge/FastAPI-0.115%2B-009688?style=flat-square&logo=fastapi&logoColor=white" alt="FastAPI" /></a>
    <a href="https://github.com/astral-sh/uv"><img src="https://img.shields.io/badge/package%20manager-uv-de5fe9?style=flat-square" alt="uv" /></a>
    <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-yellow.svg?style=flat-square" alt="License: MIT" /></a>
    <img src="https://img.shields.io/badge/tests-59%2F59%20passing-brightgreen?style=flat-square" alt="Tests" />
    <img src="https://img.shields.io/badge/privacy-100%25%20local-success?style=flat-square" alt="Privacy" />
  </p>

  <p align="center">
    <a href="#-quick-start">Quick Start</a> •
    <a href="#-the-philosophy">Why Daily Brief</a> •
    <a href="#-features">Features</a> •
    <a href="#-architecture">Architecture</a> •
    <a href="#-commands">Commands</a> •
    <a href="#-star-history">Star History</a>
  </p>
</div>

---

## ☕ Why The Daily Brief?

Every morning begins the same way: you open your laptop, and within 60 seconds you're buried under **15 open browser tabs** — Gmail, Linear, Obsidian, Slack, calendars, news feeds. It's overwhelming, disjointed, and noisy.

**The Daily Brief** replaces the morning tab avalanche with a **single, private, beautifully printed newspaper front page**:

* ⚡ **Wakes with your laptop**: Fires automatically when your MacBook wakes from sleep.
* ☕ **Synthesized for morning focus**: Reads your unread emails, urgent calendar items, and open Obsidian tasks.
* 📰 **Broadsheet typography**: Designed with classic editorial serif typography (Playfair Display & Newsreader) and tactile paper textures.
* 🔒 **100% Local & Private**: No third-party SaaS, no data tracking. Your emails, tokens, and notes stay on your machine.
* 🤖 **AI-curated**: An LLM acts as your private managing editor, extracting key action items and summarizing overnight dispatches.

---

## 🗞️ Features

* **Bespoke Broadsheet Layout** — Crafted like an authentic print newspaper with lead stories, two-column dispatch sections, day/night broadsheet toggle, and ink rubber-stamp seals.
* **MacBook Wake Trigger** — Triggers seamlessly upon opening your MacBook lid, so your daily edition is already waiting when you sit down with your coffee.
* **Multi-Space Desks** — Isolate distinct areas of your life (e.g. `Personal`, `Work`, `Research`, `Crypto`) with independent connectors and folders.
* **Gmail Connector with Deep Audit** — Secure OAuth2 loopback authentication. Distinguishes between urgent starred messages and background newsletters.
* **Obsidian Vault Sync** — Scans your daily notes and project files for open tasks (`- [ ]`), stalled deadlines, and project milestones.
* **The Telegraph Wire (Global Feed)** — A unified cross-space feed summarizing all active desks into a single master edition.
* **Interactive Local Hub (`localhost:8000`)** — Built-in FastAPI dashboard to manage spaces, trigger instant dispatches, authorize OAuth with 1 click, and run real-time connection diagnostics.
* **Pluggable LLM Providers** — Preconfigured for Gemini (`gemini-flash-lite`), OpenAI (`gpt-4o-mini`), or local Ollama models.

---

## 🚀 Quick Start

Get your morning newspaper running locally in under **60 seconds**:

### 1. Clone & Install

```bash
# Clone the repository
git clone https://github.com/soroqn1/The-Daily-Brief.git
cd The-Daily-Brief

# Install dependencies with uv
uv sync
```

### 2. Configure Environment

Copy the example environment file and add your LLM API key:

```bash
cp .env.example .env
```

Edit `.env`:
```ini
# Add your Gemini or OpenAI API key
GEMINI_API_KEY="your-gemini-api-key"
# or OPENAI_API_KEY="your-openai-api-key"
```

### 3. Launch Local Hub

```bash
task serve
```

Visit **[http://localhost:8000](http://localhost:8000)** in your browser:
* 🔐 Click **Connect → Authorize with Google** to connect Gmail with 1 click.
* 📝 Point the Obsidian connector to your local vault directory (e.g. `~/me/obsidian`).
* ⚡ Click **Regenerate** to read your first morning edition!

---

## 🧩 Architecture

```
                                 ┌────────────────────────┐
                                 │   MacBook Wake Event   │
                                 └───────────┬────────────┘
                                             │
                                             ▼
                               ┌──────────────────────────┐
                               │       Orchestrator       │
                               │  (the_daily_brief.main)  │
                               └─────────────┬────────────┘
                                             │
               ┌─────────────────────────────┼─────────────────────────────┐
               ▼                             ▼                             ▼
       ┌───────────────┐             ┌───────────────┐             ┌───────────────┐
       │     Gmail     │             │   Obsidian    │             │   Calendar    │
       │   Connector   │             │   Connector   │             │  (Pluggable)  │
       └───────┬───────┘             └───────┬───────┘             └───────┬───────┘
               │                             │                             │
               └───────────────────────┬─────┴─────────────────────────────┘
                                       │ Raw BriefItems
                                       ▼
                       ┌───────────────────────────────┐
                       │          LLM Client           │
                       │ (Gemini Flash / OpenAI / etc) │
                       └───────────────┬───────────────┘
                                       │ Structured BriefData JSON
                                       ▼
                       ┌───────────────────────────────┐
                       │        Jinja2 Renderer        │
                       │     (Broadsheet Template)     │
                       └───────────────┬───────────────┘
                                       │
                      ┌────────────────┴────────────────┐
                      ▼                                 ▼
         ┌─────────────────────────┐       ┌─────────────────────────┐
         │       daily.html        │       │        daily.md         │
         │  (Opens in Web Browser) │       │   (Raw feed for AI)     │
         └─────────────────────────┘       └─────────────────────────┘
```

---

## 💻 CLI & Taskfile Commands

The Daily Brief comes with a developer-first `Taskfile.yml`:

| Command | Description |
| :--- | :--- |
| `task serve` | Start local FastAPI server with live reload on `http://localhost:8000` |
| `task brief-now` | Immediately fetch data, run LLM synthesis, and open today's brief |
| `task email-now` | Generate a deep multi-day email audit and action item list |
| `task auth-gmail` | Run interactive Google OAuth2 desktop authorization flow |
| `task test` | Run complete Pytest test suite (59 unit & integration tests) |
| `task ruff` | Run Ruff linter and code formatter checks |
| `task pre-commit` | Run full quality gate (Ruff check + format check + test suite) |

---

## 📂 Project Structure

```
The-Daily-Brief/
├── the_daily_brief/
│   ├── main.py              # Orchestrator & multi-space generation
│   ├── server.py            # Local FastAPI hub & management API
│   ├── config.py            # YAML configuration & space storage
│   ├── auth.py              # Secure Google OAuth2 loopback handler
│   ├── state.py             # Atomic state persistence (~/.the-daily-brief/)
│   ├── notifier.py          # Native macOS notifications (osascript)
│   ├── connectors/          # Pluggable data sources
│   │   ├── base.py          # BaseConnector abstract contract
│   │   ├── gmail.py         # Gmail API connector & email audit
│   │   ├── obsidian.py      # Local Obsidian markdown vault parser
│   │   └── registry.py      # Dynamic connector registry & schemas
│   ├── llm/                 # LLM provider clients
│   │   ├── base.py          # BaseLLMClient contract & diagnostics
│   │   ├── gemini.py        # Google Gemini Flash Lite client
│   │   └── openai.py        # OpenAI GPT-4o-mini client
│   └── renderer/            # Editorial Jinja2 rendering engine
│       ├── renderer.py      # HTML & Markdown builders
│       └── templates/       # Broadsheet newspaper templates
│           ├── brief.html.j2
│           ├── email_audit.html.j2
│           ├── global_feed.html.j2
│           └── dashboard.html.j2
├── docs/                    # Architecture, vision & product specs
├── tests/                   # 59 automated pytest tests
├── pyproject.toml           # Modern PEP 621 metadata & dependencies
└── Taskfile.yml             # Task runner automation
```

---

## 🔒 Security & Privacy Invariants

1. **Zero External Tracking**: No telemetry, analytics, or external tracking scripts.
2. **Local Credential Storage**: OAuth tokens and API keys are stored strictly in your local `.env` and `~/.the-daily-brief/` folder with atomic writes (`os.replace`).
3. **Loopback CORS**: The local FastAPI server restricts Cross-Origin requests strictly to `http://localhost:8000` and `http://127.0.0.1:8000`.
4. **Path Traversal Protection**: All space directories are strictly validated with regex (`^[a-zA-Z0-9_-]{1,64}$`) and restricted to the designated storage directory.
5. **Jinja2 Auto-Escaping**: All user-controlled text strings from emails and notes are strictly escaped against XSS.

---

## ⭐ Star History

If you find The Daily Brief helpful, please consider starring the repository! It helps more developers discover local-first tools:

<div align="center">
  <a href="https://star-history.com/#soroqn1/The-Daily-Brief&Date">
    <img src="https://api.star-history.com/svg?repos=soroqn1/The-Daily-Brief&type=Date" alt="Star History Chart" width="70%" />
  </a>
</div>

---

## 📄 License

Distributed under the **MIT License**. See `LICENSE` for details.

Developed with ❤️ for developers who love clean code, good coffee, and distraction-free mornings.
