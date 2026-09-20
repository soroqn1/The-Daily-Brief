# The Daily Brief — Complete Product Specification & Design Blueprint

> **A personal, local-first intelligence newspaper and multi-space command center.**  
> Designed for on-demand generation, AI pair-programming integration (Hermes, Claude, Neovim), and noise-free daily briefings.

---

## 1. Product Vision & Philosophy

### 1.1 From Automation to Intentional On-Demand Briefings
Originally conceived as an automated wake-from-sleep background script, **The Daily Brief** has evolved into an **on-demand personal intelligence hub**:
- **Zero background clutter**: No forced wake-up triggers or hidden background demons.
- **Intentional consumption**: Generated on demand when the user sits down to work — via a single click on a browser Startpage / New Tab, or a quick CLI / API call.
- **The "Gazette" Aesthetic**: Newspaper typography and editorial layout. It looks and feels like a curated morning paper, not a chaotic SaaS analytics dashboard.

### 1.2 Multi-Space Architecture (Isolation by Context)
Life and work are separated into distinct **Spaces** (e.g. `WORK`, `PERSONAL`, `CRYPTO`, `STUDY`):
- Each space has **its own data sources** (e.g., Work Gmail with independent OAuth credentials vs. Personal Gmail; Work Obsidian vault vs. Personal Notes).
- Each space generates **independent reports** saved into isolated folders.
- A **Global Unified Feed** aggregates the top highlights and urgent actions across all spaces onto a single screen.

### 1.3 Local-First & Dual-Format Persistence
- **100% Local**: No external cloud database, no tracking, no subscription fees. API keys remain strictly in local `.env`.
- **Dual-Format Output**: Every generation produces two artifacts in `~/Desktop/TheDailyBrief/<DD-MM-YY>/<space>/`:
  1. `.html` — High-craft visual document designed for human reading in the browser.
  2. `.md` — Clean, dense, structured Markdown specifically formatted for feeding into AI agents (Claude, Hermes, Neovim, Obsidian).
- **"Copy Path for AI" Button**: One-click clipboard button on every HTML report copying the absolute path to the `.md` file, allowing instant sharing with local agent workflows.

---

## 2. Core Functional Modules & Report Types

```
                               ┌────────────────────────┐
                               │ Browser Startpage / Hub│
                               └───────────┬────────────┘
                                           │
         ┌─────────────────────────────────┼────────────────────────────────┐
         ▼                                 ▼                                ▼
┌─────────────────┐             ┌─────────────────────┐          ┌──────────────────────┐
│  Global Daily   │             │ Space Daily Brief   │          │ Space Email Audit    │
│  (/global/daily)│             │ (/{space}/daily)    │          │ (/{space}/email)     │
└────────┬────────┘             └──────────┬──────────┘          └──────────┬───────────┘
         │                                 │                                │
         ▼                                 ▼                                ▼
Aggregated multi-space           Action Required, Missed,         Deep 3-7 day inbox triage:
Reddit/Bento style feed          Schedule, Tasks, AI Advice       Replies, Deadlines, Checklist
```

### 2.1 The Daily Brief (`/{space}/daily`)
The core daily front page for a specific context.
- **AI Masthead & Lead**:
  - Catchy editorial headline summarizing the tone of the day (e.g., *"Heavy morning with 3 contract reviews and standup at 11:00"*).
  - Editorial AI recommendation (e.g., *"Reply to Alex before 10:30, invoice Stripe, defer Obsidian cleanup"*).
- **Section 1: Action Required**:
  - Urgent items requiring immediate decisions, answers, or signatures. Marked with high-priority visual accents.
- **Section 2: Missed Overnight / Recent**:
  - What happened while away: newly arrived emails, notifications, project updates.
- **Section 3: Today's Schedule**:
  - Chronological timeline of meetings, calls, and deadlines. If no meetings: clean *"All clear ✓"* indicator.
- **Section 4: Tasks & Goals**:
  - Unfinished tasks, stalled projects, and TODOs pulled directly from Obsidian or project notes.

### 2.2 Deep Email Audit (`/{space}/email`)
A specialized diagnostic scan of the inbox over the last 3–7 days to answer the critical question: *"Did I drop any balls or miss important correspondence?"*
- **Triage Statistics**: Total emails scanned, response pending count, active commitments count.
- **Category 1: Needs Your Reply**:
  - Direct emails addressed to the user requiring a response, sorted by urgency and waiting time.
- **Category 2: Commitments & In-Flight**:
  - Things the user promised to deliver, or waiting on someone else's promised deliverable.
- **Category 3: Deadlines & Urgent**:
  - Expiring links, billing notices, project deadlines, upcoming event registrations.
- **Category 4: Actionable Checklist**:
  - A consolidated, copyable checklist of discrete follow-up actions to clear the inbox.

### 2.3 Unified Global Feed (`/global/daily`)
A single, cohesive stream bringing together all active spaces:
- Top cross-space **Urgent Action Alert** bar.
- Space-by-space cards arranged in a responsive Bento / Newspaper column grid.
- Allows browsing the entire day at a glance without navigating between separate spaces.

### 2.4 Real-Time Diagnostics & Health Testing
- **LLM Connectivity Ping**:
  - Diagnostic ping sends `"ping"` to the configured model (Gemini / OpenAI).
  - Displays the model's actual textual response in the UI (e.g., `💬 Model response to "ping": "pong"`).
- **Connector Health Verification**:
  - Live token validation (verifies OAuth tokens against Google's token endpoint).
  - Explicit error reporting (detects revoked tokens, expired grants, or malformed credentials).
- **Non-blocking Warnings**:
  - If a connector fails during brief generation, the brief is still generated with available data, and a warning banner appears at the top of the report explaining what was skipped.

---

## 3. Screen-by-Screen UI / UX Specifications

Below are the detailed specifications for every screen, modal, and view required for the UI design.

```
Pages to Design:
1. Local Hub / Management Dashboard   (Route: / or /settings)
2. Daily Brief Human View             (Route: /{space}/daily)
3. Deep Email Audit View              (Route: /{space}/email)
4. Unified Global Feed Startpage      (Route: /global/daily)

Modals & Overlays to Design:
5. "+ Add Space" Modal
6. "+ Add Connect" (Connector Wizard) Modal
7. OAuth Success / Error Callback Window
```

---

### Screen 1: Local Hub / Management Dashboard (`/` or `/settings`)

The administrative headquarters and home screen of The Daily Brief.

#### Layout Structure
1. **Header Bar**:
   - Left: Masthead logo **The Daily Brief** (Georgia / Serif font) + subtle version/build badge.
   - Center: Subtitle *"Local Intelligence Hub & Multi-Space Manager"*.
   - Right: Quick Action Buttons:
     - `🌐 Global Feed` (direct link to `/global/daily`)
     - `+ New Space` (opens Add Space modal)
     - Theme toggle (Light / Dark).

2. **Global Feed Quick-Launcher Banner**:
   - A hero card providing one-click access to regenerate or view the multi-space global feed.
   - Status tag: `Last generated: Today at 09:15` or `Not generated yet`.
   - Action buttons: `Open Global Feed`, `⚡ Regenerate All`.

3. **Spaces Grid (Cards)**:
   - Dynamic grid displaying each configured Space (e.g., `WORK`, `PERSONAL`, `CRYPTO`).
   - **Space Card Header**:
     - Space Name in uppercase bold with accent color tag.
     - Filesystem path display (e.g., `~/Desktop/TheDailyBrief/20-09-26/work/`).
     - Space Controls: `⚡ Test Connections`, `+ Add Connect`, `🗑️ Delete Space`.
   - **Diagnostics Dropdown / Collapsible Panel**:
     - Appears upon clicking `⚡ Test Connections`.
     - Displays LLM test status:
       - `✅ LLM (gemini): Gemini API connected (gemini-3-flash-preview, key active)`
       - Sub-block: `💬 Model response to "ping": "pong"`
     - Displays status of each connector in the space (e.g., `✅ GMAIL: Gmail API active`, `❌ GMAIL: Token expired`).
   - **Connected Sources List**:
     - Chip badges representing active connectors:
       - `[GMAIL] Work Gmail (scan_hours: 24) [×]`
       - `[OBSIDIAN] Main Vault (/notes) [×]`
     - Empty state hint if no connectors exist: *"No sources connected yet. Click '+ Add Connect' to link an inbox or vault."*
   - **Reports Action Rows**:
     - **Daily Brief Row**:
       - Status badge (`Generated ✓` in green or `Not yet generated` in gray).
       - Buttons: `Open` (Primary), `Regenerate` (Secondary), `Raw .md` (Ghost).
     - **Email Audit Row**:
       - Status badge (`Generated ✓` or `Not yet generated`).
       - Buttons: `Open` (Primary), `Regenerate` (Secondary), `Raw .md` (Ghost).

---

### Screen 2: The Daily Brief View (`/{space}/daily`)

The flagship "morning newspaper" experience for a specific space.

#### Visual Structure
1. **Top Utility Bar** (Sticky / Minimal):
   - Left: Space Badge (`← Hub`, Space Name `WORK`).
   - Right:
     - `📋 Copy Path for AI` (Copies markdown file path to clipboard with animation: *"Copied! Paste into Hermes/Claude"*).
     - `View Raw Markdown` (links to `/{space}/daily/raw`).
     - `🔄 Regenerate Brief`.

2. **Warning Banner** (Conditional):
   - Appears only if a connector was unreachable or skipped.
   - Style: Soft amber background, warning icon, concise message:
     *"⚠️ Gmail connection warning: Refresh token expired. Report generated from remaining sources."*

3. **Newspaper Masthead**:
   - Centered large classic serif title: **THE DAILY BRIEF**
   - Sub-bar with double-line divider:
     `SPACE: WORK` · `DATE: MONDAY, SEP 21, 2026` · `EDITION #42` · `STATUS: COMPLETE`

4. **The Lead / Editorial Section**:
   - Headline: Large serif font, italicized or quoted (e.g., *"Heavy morning: 3 pending contract reviews and team standup at 11:00"*).
   - Editorial Recommendation Callout:
     - Clean ivory/cream tinted card with left accent border.
     - Text: *"Focus on Alex's review first. Postpone the backlog grooming to afternoon."*

5. **Content Columns / Sections**:
   - **Section 1: ACTION REQUIRED**
     - Header: Bold uppercase serif with red accent dot or badge count.
     - Items: Card or clean list item with:
       - Source badge: `[gmail]` or `[obsidian]` in subtle gray monospace.
       - Item Title: High-contrast bold link.
       - LLM Summary: 1–2 crisp sentences explaining the urgency.
       - Deep Link: External arrow link (`↗ Open Email` or `↗ Open in Obsidian`).
   - **Section 2: MISSED OVERNIGHT / RECENT**
     - Grouped summary of messages, newsletters, or notifications received while offline.
   - **Section 3: TODAY'S SCHEDULE**
     - Timeline view: Time pill (`10:00 AM`), Meeting title, participants/calendar badge.
     - Empty state: *"All clear ✓ No events scheduled for today."*
   - **Section 4: TASKS & GOALS**
     - Open TODOs extracted from Obsidian daily notes or task files.
     - Checkbox visual style (read-only), tagged with project name.

6. **Footer**:
   - Storage confirmation: *"Saved locally to ~/Desktop/TheDailyBrief/20-09-26/work/daily.html & daily.md"*
   - Timestamp and model metadata (`Generated at 09:14 via gemini-3-flash-preview`).

---

### Screen 3: Deep Email Audit View (`/{space}/email`)

Designed for deep inbox triage and zero-inbox audits across 3–7 days.

#### Visual Structure
1. **Top Utility Bar**:
   - Same consistency: `← Back to Hub`, Space Selector, `📋 Copy Path for AI`, `🔄 Re-run Audit`.

2. **Masthead & Audit Scope**:
   - Title: **INBOX AUDIT & PENDING TRIAGE**
   - Metadata Pills:
     - ⏱️ `Audit Scope: Last 5 Days`
     - ✉️ `142 Emails Analyzed`
     - ⚠️ `5 Awaiting Reply`
     - 📌 `3 Pending Commitments`

3. **Audit Grid / Sections**:
   - **Category 1: Needs Your Reply** (Red/Amber priority accent):
     - Emails addressed specifically to the user where the other party is waiting for an answer.
     - Includes: Sender avatar/name, date sent, hours elapsed, subject, summary of what they asked.
   - **Category 2: Commitments & In-Flight** (Blue/Indigo accent):
     - Promises made by the user (*"I'll send the draft by Tuesday"*) or waiting on external deliverable.
   - **Category 3: Deadlines & Urgent** (Red accent):
     - Invoices, contracts expiring, registrations, time-sensitive alerts.
   - **Category 4: Next Steps Checklist**:
     - Interactive / copyable checklist block with checkboxes for clearing each pending item.

---

### Screen 4: Unified Global Feed Startpage (`/global/daily`)

Ideal as a custom browser home tab / new tab.

#### Visual Structure
1. **Top Bar**:
   - Morning Greeting: *"Good morning. Here is your overview across all spaces."*
   - Date & Time widget.
   - Space Quick-Jump Chips: `All Spaces`, `Work`, `Personal`, `Crypto`, `Settings`.

2. **Urgent Action Command Center**:
   - Full-width callout strip consolidating all urgent items across all spaces at the very top.
   - Example:
     - `[WORK · GMAIL]` Contract from Alex (awaiting signature)
     - `[PERSONAL · GMAIL]` Flight check-in available

3. **Bento Grid of Spaces**:
   - Multi-column layout where each space has a distinct column or card tile:
     - Tile Header: Space title with custom accent dot.
     - Top 3 items from that space.
     - Direct button to open full space daily brief.

---

### Modal 1: "+ Add Space" Modal

A lightweight, centered modal overlay.
- **Title**: *Create New Space*
- **Form Fields**:
  - `Space Identifier`: text input (e.g. `work`, `trading`, `freelance`). Auto-slugified (lowercase, dashes).
- **Helper text**: *"Spaces isolate your data, credentials, and briefs into dedicated directories."*
- **Actions**:
  - `Cancel` (secondary button)
  - `Create Space` (primary black button)

---

### Modal 2: "+ Add Connect" (Connector Setup Wizard)

An interactive modal guiding the user through connecting new sources without config file editing.

#### Modal Structure
1. **Step 1: Space & Provider Selection**:
   - Dropdown 1: `Select Space` (pre-selected from active card).
   - Dropdown 2: `Source Type`:
     - ✉️ **Google Gmail** (OAuth 2.0)
     - 📓 **Obsidian Vault** (Local markdown parser)
     - 📅 **Google Calendar** (Planned)
     - 💬 **Telegram / Slack** (Planned)

2. **Step 2: Interactive In-Modal Guide Box**:
   - Collapsible, styled step-by-step instructions:
     - Step 1: Open Google Cloud Console (direct link opens in new tab).
     - Step 2: Create OAuth Client ID with type **Desktop App**.
     - Step 3: Copy Client ID and Client Secret into the fields below.
   - Auto-save notice badge: `🔑 Refresh token will be saved to .env as GMAIL_REFRESH_TOKEN_<SPACE>`.

3. **Step 3: Dynamic Fields Form**:
   - **For Gmail**:
     - Input 1: `Client ID` (`...apps.googleusercontent.com`)
     - Input 2: `Client Secret` (with client-side validation preventing pasting of Client ID into Secret field).
     - Direct Action Button: `🔐 Authorize with Google in Browser`.
       - Opens pop-up window to `http://localhost:8000` OAuth consent screen.
       - Token is exchanged automatically, written to `.env`, and modal shows green checkmark.
   - **For Obsidian**:
     - Input 1: `Vault Directory Path` (e.g. `/Users/username/notes`).
     - Input 2: `Target Directories` (comma-separated, e.g. `Daily, Projects`).
     - Input 3: `Scan Days` (number input, default 3).

4. **Footer Actions**:
   - `Cancel` button.
   - `Save & Connect` button.

---

## 4. Design System & Typography Guidelines

To maintain the high-craft "Morning Gazette" identity while supporting modern dark mode and AI agent readability:

### 4.1 Typography Pairing
| Role | Font Family | Fallbacks | Usage |
|------|-------------|-----------|-------|
| **Masthead & Big Headlines** | `Playfair Display` or `Newsreader` | Georgia, serif | Brand titles, daily headlines, section titles |
| **Body & UI Controls** | `Inter` or `-apple-system` | SF Pro, sans-serif | Descriptions, email bodies, buttons, form inputs |
| **Tags, Paths & Code** | `JetBrains Mono` or `SF Mono` | Menlo, monospace | Source tags (`[gmail]`), file paths, env keys |

### 4.2 Color System

#### Light Theme (Editorial Print)
- **Background**: `#FAFAFA` (soft newspaper paper tone)
- **Card Background**: `#FFFFFF` (clean white)
- **Surface / Ivory Tint**: `#F4F4F3`
- **Text Primary (Ink)**: `#111111` (rich black)
- **Text Secondary**: `#555555` (muted lead text)
- **Text Muted**: `#888888` (timestamps, file paths)
- **Borders & Dividers**: `#E5E5E5`
- **Urgent Accent**: `#DC2626` (classic editorial red)
- **AI Recommendation Accent**: `#4F46E5` / `#6366F1` (indigo/violet callout border)
- **Success Accent**: `#16A34A` (green checkmarks)

#### Dark Theme (Midnight Edition)
- **Background**: `#0F0F10`
- **Card Background**: `#18181B`
- **Surface Tint**: `#27272A`
- **Text Primary**: `#F4F4F5`
- **Text Secondary**: `#A1A1AA`
- **Borders**: `#27272A`
- **Urgent Accent**: `#EF4444`

### 4.3 Key Component Patterns
- **Chips & Badges**: Small rounded-full or rounded-sm badges with 1px subtle border, uppercase 10px tracking.
- **Double Hairline Dividers**: Classic newspaper double-border rule separating headers from content:
  ```css
  border-top: 1px solid #111;
  border-bottom: 1px solid #111;
  padding: 4px 0;
  ```
- **"Copy Path for AI" Button**:
  - Distinctive icon button with clipboard glyph.
  - Hover effect with instant visual feedback tooltip.

---

## 5. Complete REST API & Integration Reference

All UI pages interact with the local FastAPI backend running on `http://localhost:8000`:

| Method | Route | Description | Output |
|--------|-------|-------------|--------|
| `GET` | `/` or `/settings` | Serves Local Hub dashboard HTML | `text/html` |
| `GET` | `/global/daily` | Serves unified multi-space daily feed HTML | `text/html` |
| `POST` | `/global/daily` | Force regenerates unified global feed | `application/json` |
| `GET` | `/global/daily/raw` | Serves raw Markdown of global feed | `text/plain` |
| `GET` | `/{space}/daily` | Serves space daily brief HTML | `text/html` |
| `POST` | `/{space}/daily` | Force regenerates space daily brief | `application/json` |
| `GET` | `/{space}/daily/raw` | Serves raw Markdown of space brief | `text/plain` |
| `GET` | `/{space}/email` | Serves space deep email audit HTML | `text/html` |
| `POST` | `/{space}/email` | Force regenerates deep email audit | `application/json` |
| `GET` | `/{space}/email/raw` | Serves raw Markdown of email audit | `text/plain` |
| `GET` | `/api/spaces` | Lists all configured spaces & connectors | `application/json` |
| `POST` | `/api/spaces` | Creates a new space (`{"name": "..."}`) | `application/json` |
| `DELETE` | `/api/spaces/{space}` | Deletes a space and its config | `application/json` |
| `GET` | `/api/connector-types` | Lists available connector types with guides & schema | `application/json` |
| `POST` | `/api/spaces/{space}/connectors` | Adds or updates a connector in a space | `application/json` |
| `DELETE` | `/api/spaces/{space}/connectors/{id}`| Removes a connector from a space | `application/json` |
| `GET` | `/api/spaces/{space}/diagnostics` | Tests LLM ("ping") & space connectors | `application/json` |
| `POST` | `/api/auth/gmail/prepare` | Stores Client ID & Secret before OAuth | `application/json` |
| `GET` | `/api/auth/gmail/start` | Initiates Google OAuth consent redirect | `307 Redirect` |
| `GET` | `/api/auth/gmail/callback` | OAuth loopback endpoint receiving auth code | `text/html` |

---

## 6. Directory & File Storage Contract

```
~/Desktop/TheDailyBrief/
└── <DD-MM-YY>/                      # e.g., 20-09-26
    ├── global/
    │   ├── daily.html               # Multi-space unified web feed
    │   └── daily.md                 # Multi-space unified AI markdown
    ├── work/
    │   ├── daily.html               # Human visual newspaper
    │   ├── daily.md                 # Agent-ready structured markdown
    │   ├── email.html               # Deep inbox audit web view
    │   └── email.md                 # Deep inbox audit markdown
    └── personal/
        ├── daily.html
        └── daily.md
```

This specification gives complete architectural, functional, and visual parameters required to craft the ultimate UI designs for every screen and interaction in **The Daily Brief**.
