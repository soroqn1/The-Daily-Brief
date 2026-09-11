# The Daily Brief — Architecture

## System Overview

```
[Mac wakes from sleep]
        │
        ▼
[launchd LaunchAgent]
        │  (if time >= 09:00 AND no brief today)
        ▼
[main.py — orchestrator]
        │
        ├─── [connector: gmail]    ─┐
        ├─── [connector: obsidian] ─┤ → List[BriefItem] (async, parallel)
        ├─── [connector: calendar] ─┤
        └─── [connector: ...]     ─┘
                                    │
                                    ▼
                            [LLM client]
                       single call, structured JSON input
                       (sections tagged: [email], [obsidian], etc.)
                                    │
                                    ▼ JSON response
                            [renderer / Jinja2]
                                    │
                                    ▼ .html file
                        ~/.the-daily-brief/briefs/YYYY-MM-DD.html
                                    │
                                    ▼
                        [open in browser] + [cleanup: >7 days]
```

---

## Repository Structure

```
the-daily-brief/
├── the_daily_brief/
│   ├── __init__.py
│   ├── main.py              # entry point, orchestrator
│   ├── config.py            # loads config.yaml + .env
│   ├── state.py             # read/write ~/.the-daily-brief/state.json
│   ├── connectors/
│   │   ├── base.py          # BaseConnector ABC → fetch() → List[BriefItem]
│   │   ├── gmail.py
│   │   ├── obsidian.py
│   │   ├── calendar.py      # phase 2
│   │   └── telegram.py      # phase 2
│   ├── llm/
│   │   ├── base.py          # BaseLLMClient ABC
│   │   ├── gemini.py
│   │   └── openai.py
│   ├── renderer/
│   │   ├── renderer.py      # BriefData → HTML via Jinja2
│   │   └── templates/
│   │       └── brief.html.j2
│   └── notifier.py          # macOS osascript notifications
├── trigger/
│   └── com.dailybrief.plist # launchd LaunchAgent
├── config.yaml              # user-facing config
├── .env.example             # token references (never committed)
├── pyproject.toml           # uv / PEP 517
├── Taskfile.yml
└── docs/
    ├── vision.md
    └── architecture.md
```

---

## Data Model

### BriefItem — universal connector output

```python
@dataclass
class BriefItem:
    source: str  # "gmail" | "obsidian" | "calendar" | ...
    category: str  # "missed" | "action_required" | "schedule" | "task"
    title: str  # short headline
    body: str  # raw content (truncated to ~300 chars)
    priority: int  # 1 = urgent, 2 = normal, 3 = fyi
    timestamp: datetime | None
    url: str | None  # deep link if applicable
```

### BriefData — LLM JSON output schema

```json
{
  "headline": "Your day looks busy — here's what matters",
  "missed": [{"title": "...", "summary": "...", "source": "gmail"}],
  "action_required": [{"title": "...", "summary": "...", "source": "gmail"}],
  "schedule": [{"time": "14:00", "title": "...", "source": "calendar"}],
  "tasks": [{"title": "...", "status": "open", "source": "obsidian"}],
  "ai_recommendation": "Reply to X before 12:00, close task Y"
}
```

---

## Connector Contract

```python
class BaseConnector(ABC):
    name: str  # connector id, matches config key

    @abstractmethod
    async def fetch(self) -> list[BriefItem]:
        """Fetch data since last brief timestamp. Never raises — logs + returns []."""
```

Adding a new source:
1. Create `connectors/my_source.py` implementing `BaseConnector`
2. Add section to `config.yaml` with `enabled: true`
3. Done — orchestrator discovers it automatically by config key

---

## config.yaml — User-Facing Config

```yaml
output_dir: ~/.the-daily-brief        # where briefs & state are stored
brief_after_hour: 9               # don't generate before this hour
brief_language: en

llm:
  provider: gemini                 # gemini | openai
  model: gemini-2.0-flash

connectors:
  gmail:
    enabled: true
    max_emails: 20
    scan_hours: 12                 # look back 12h

  obsidian:
    enabled: true
    vault_path: ~/me/obsidian
    scan_dirs: ["50 Daily", "10 Projects"]

  calendar:
    enabled: false                 # phase 2
```

---

## Secrets (.env)

```dotenv
GEMINI_API_KEY=...
OPENAI_API_KEY=...
GMAIL_CLIENT_ID=...
GMAIL_CLIENT_SECRET=...
GMAIL_REFRESH_TOKEN=...
TELEGRAM_API_ID=...
TELEGRAM_API_HASH=...
```

- `.env` is in `.gitignore`, never committed
- `config.yaml` references only keys, no values

---

## Trigger: launchd LaunchAgent

File: `~/Library/LaunchAgents/com.dailybrief.plist`

```xml
<key>StartOnMount</key><true/>
<!-- fires on wake-from-sleep -->
```

Logic inside the script (not inside plist):
- Check `state.json` → if `last_brief_date == today` → exit
- Check `datetime.now().hour >= config.brief_after_hour` → else exit
- Run brief → save `last_brief_date = today`

---

## Error Handling

| Situation | Behaviour |
|-----------|-----------|
| Connector fails (network, auth) | Skip connector, log warning, note in brief |
| LLM API fails | macOS error notification, log error, exit |
| Brief already generated today | Silent exit (idempotent) |
| Time < 09:00 | Silent exit |

---

## Execution Flow (main.py)

```python
async def run():
    state = load_state()
    if state.brief_generated_today or too_early():
        return

    items = await asyncio.gather(*[c.fetch() for c in active_connectors], return_exceptions=True)
    flat_items = flatten_and_filter(items)  # drop failed connectors

    brief_json = await llm.generate(flat_items)
    html = renderer.render(brief_json)

    path = save_brief(html)
    state.mark_done()
    open_in_browser(path)
    cleanup_old_briefs(keep=7)
```

---

## Phased Roadmap

| Phase | Features |
|-------|----------|
| **1 — MVP** | Gmail + Obsidian · launchd trigger · Gemini/OpenAI · Jinja2 HTML |
| **2** | Google Calendar · Telegram |
| **3** | Slack · IMAP (work email) · GitHub PRs |
| **Future** | Weekly AI rollup · In-browser archive browser |
