# Anna Platform Guide & GitProject Analyzer Setup

This document covers two things:
1. **Part A** — A general guide to the Anna platform: what it is, how to set it up, and how to build apps for it.
2. **Part B** — The complete record of building, debugging, and publishing the **GitProject Analyzer** app on Anna.

---

# Part A: Understanding the Anna Platform

## What is Anna?

Anna is an **AI-native application platform**. Think of it as an app store, but every app has built-in access to powerful AI models (LLMs) — for free. Developers build small, focused apps that run inside the Anna desktop environment, and the platform handles all the AI infrastructure behind the scenes.

### Key concepts:
- **Anna Desktop** — The main application users install on their PC. It provides a workspace with an AI assistant and a marketplace of apps.
- **Anna Apps** — Small web apps (HTML/JS/CSS) that run inside Anna's desktop environment. They can call AI models, invoke backend tools, and interact with the user through a custom UI.
- **Executas** — Backend plugins written in Python, Node.js, or Go. They run server-side (or locally during development) and perform the heavy lifting — API calls, data processing, file operations, etc. An Executa is essentially a "tool" that the AI can use.
- **Anna CLI** (`anna-app`) — The command-line tool developers use to scaffold, develop, test, and publish apps.

### How it all fits together:

```
┌──────────────────────────────────────────────────────┐
│                   Anna Desktop App                    │
│                                                       │
│  ┌─────────────────────┐  ┌────────────────────────┐ │
│  │   Your App's UI      │  │   Anna AI Assistant    │ │
│  │   (bundle/)          │  │   (built-in chat)      │ │
│  │                      │  │                         │ │
│  │  index.html          │  │  Can use your Executa  │ │
│  │  app.js              │  │  tools automatically   │ │
│  │  style.css           │  │                         │ │
│  └──────────┬───────────┘  └────────────┬───────────┘ │
│             │                           │              │
│             ▼                           ▼              │
│  ┌──────────────────────────────────────────────────┐ │
│  │              Anna Platform APIs                   │ │
│  │                                                   │ │
│  │  anna.tools.invoke()  →  Calls your Executa      │ │
│  │  anna.llm.complete()  →  Calls AI models (free)  │ │
│  │  anna.window.*        →  Controls the UI window  │ │
│  └──────────────────────────────────────────────────┘ │
│                          │                             │
│                          ▼                             │
│  ┌──────────────────────────────────────────────────┐ │
│  │           Your Executa (Python/Node/Go)           │ │
│  │                                                   │ │
│  │  Runs your backend logic:                         │ │
│  │  - API calls, data processing, git clone, etc.   │ │
│  │  - Communicates via JSON-RPC over stdin/stdout    │ │
│  └──────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────┘
```

### Why build on Anna instead of a standalone app?
1. **Free AI** — Anna provides hosted LLM access via `anna.llm.complete()`. Your users don't need their own API keys.
2. **Zero deployment** — No need to set up servers, domains, or hosting. Anna hosts your frontend and runs your backend.
3. **Distribution** — Publish to the Anna app marketplace and get discovered by users instantly.
4. **Agent integration** — Your Executa tools can be used by the Anna AI assistant autonomously, even without your custom UI.

---

## How to Set Up Anna on Your PC

### Prerequisites
- **Windows 10/11** (Mac and Linux also supported)
- **Node.js** (v18 or newer) — [Download](https://nodejs.org/)
- **Python 3.10+** and **uv** (Python package manager) — [Install uv](https://docs.astral.sh/uv/getting-started/installation/)
- **Git** — [Download](https://git-scm.com/downloads)

### Step 1: Install the Anna Desktop App
Download and install the Anna desktop application from [anna.partners](https://anna.partners). Create an account and sign in.

### Step 2: Install the Anna CLI
Open PowerShell and run:
```powershell
npm install -g @anna-ai/cli
```

If you get a `PSSecurityException` error on Windows, first run:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### Step 3: Log in to the CLI
Authenticate your terminal with your Anna account:
```powershell
anna-app login --host https://anna.partners
```
This opens a browser window where you confirm the login. After that, all CLI commands are authenticated.

### Step 4: Verify installation
```powershell
anna-app --version
```
You should see something like `v0.1.30` or newer.

---

## How to Build Apps for Anna (General Guide)

### Project Structure

Every Anna App follows this structure:

```
my-app/
├── bundle/                    # Frontend (what users see)
│   ├── index.html             # Main HTML page
│   ├── app.js                 # JavaScript logic
│   └── style.css              # Styles
├── executas/
│   └── my-tool/               # Backend plugin
│       ├── my_tool.py         # Your Python code
│       ├── executa.json       # Tool identity config
│       └── pyproject.toml     # Python build config
└── manifest.json              # App configuration
```

### Step 1: Create the manifest

`manifest.json` is the heart of your app. It declares what permissions you need and what Executas you use:

```json
{
  "schema": 2,
  "permissions": ["tools.invoke"],
  "required_executas": [
    {
      "tool_id": "bundled:my-tool",
      "min_version": "0.1.0",
      "version": "latest"
    }
  ],
  "ui": {
    "bundle": {
      "format": "static-spa",
      "entry": "index.html"
    },
    "views": [
      {
        "name": "main",
        "title": "My App",
        "default": true,
        "entry": "index.html",
        "min_size": { "w": 460, "h": 600 },
        "default_size": { "w": 800, "h": 800 },
        "resizable": true,
        "movable": true,
        "single_instance": true
      }
    ],
    "host_api": {
      "llm": ["complete"],
      "window": ["set_title"]
    }
  }
}
```

> **Warning:** Do NOT add any extra fields to the manifest. Anna's backend uses strict validation and will crash with a 500 error on unknown keys.

### Step 2: Build the Frontend

Your frontend is plain HTML/JS/CSS. The key is importing the Anna SDK and connecting to the runtime:

```javascript
import { AnnaAppRuntime } from "/static/anna-apps/_sdk/latest/index.js";

async function init() {
  const anna = await AnnaAppRuntime.connect();

  // Call your backend tool
  const result = await anna.tools.invoke({
    tool_id: "bundled:my-tool",
    method: "my_method",
    args: { key: "value" }
  });

  // Call the AI (free, no API key needed)
  const llmResult = await anna.llm.complete({
    messages: [{ role: "user", content: "Explain this..." }],
    max_tokens: 2000
  });

  // The AI response text is at:
  const text = llmResult.content?.text;
}

init();
```

### Step 3: Build the Executa (Python Backend)

Create `executa.json`:
```json
{
  "slug": "my-tool",
  "name": "My Tool",
  "version": "0.1.0",
  "executa_type": "tool",
  "tool_id": "tool-my-app-my-tool-1",
  "type": "python",
  "enabled": true
}
```

Create `pyproject.toml`:
```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "tool-my-app-my-tool-1"
version = "0.1.0"
dependencies = ["requests"]

[project.scripts]
tool-my-app-my-tool-1 = "my_tool:main"
```

Your Python script communicates via JSON-RPC over stdin/stdout. The critical response format is:
```python
# Tool results MUST use this exact schema:
return {
    "success": True,
    "tool": tool_name,
    "data": { "your_key": "your_value" }
}

# Do NOT use: { "content": [...] }  — this will be rejected!
```

### Step 4: Run locally
```powershell
anna-app dev --slug my-app
```

### Step 5: Publish

```powershell
# 1. Publish the Executa
cd executas/my-tool
anna-app executa publish

# 2. Update manifest.json with the real tool_id from step 1

# 3. Push the app
cd ../..
anna-app apps push

# 4. Cut a version
anna-app apps cut 0.1.0

# 5. Submit for review
anna-app apps submit-review my-app

# 6. After approval, release it
anna-app apps release 0.1.0
```

---
---

# Part B: GitProject Analyzer — Development Journey


## 1. Initial Environment Setup

Before writing any Anna-specific code, we ensured the local environment was ready:

* **Node.js** and **uv** (Python package manager) were already installed.
* We fixed a PowerShell execution policy error (`PSSecurityException`) by running:
  ```powershell
  Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
  ```
* We installed the official Anna CLI globally:
  ```powershell
  npm install -g @anna-ai/cli
  ```
* We logged into the Anna developer console from the terminal:
  ```powershell
  anna-app login --host https://anna.partners
  ```

---

## 2. Project Architecture

We structured the project to follow the standard Anna App format:

```
gitproject analyzer/
├── bundle/                          # Frontend (HTML/JS/CSS)
│   ├── index.html
│   ├── app.js
│   ├── style.css
│   └── anna-tool-ids.js            # Auto-generated by anna-app push
├── executas/
│   └── github-fetcher/             # Backend Python Executa plugin
│       ├── github_fetcher.py       # Core logic (GitHub API + git clone)
│       ├── executa.json            # Executa identity config
│       ├── pyproject.toml          # Python build config (hatchling)
│       └── run_local.py            # Standalone local test runner
├── manifest.json                    # Anna App manifest
├── runner.bat                       # Local batch file runner
└── .anna/
    └── app.json                    # Auto-generated app identity (after push)
```

### Key files explained:
- **`manifest.json`** — Declares permissions (`tools.invoke`), registers the Executa, defines the UI views, and configures the LLM scopes.
- **`executa.json`** — Identifies the Python backend plugin (slug, tool_id, version).
- **`bundle/app.js`** — The frontend JavaScript that calls `anna.tools.invoke()` to run the Executa and `anna.llm.complete()` to get AI analysis.

---

## 3. The 3 Major Bugs We Squashed During Development

### Bug #1: The Missing Python Build System
When running `anna-app dev`, the local harness tried to start our Python Executa using `uv run`. It crashed because `github_fetcher.py` was a standalone script without a build configuration.

**Fix:** Updated `pyproject.toml` to include the `hatchling` build system and a proper `[project.scripts]` entry point.

### Bug #2: The Strict `manifest.json` (500 Error)
Because the project folder contained a space (`"gitproject analyzer"`), the CLI threw errors. We tried adding `"slug"` and `"name"` to `manifest.json`, but the Anna Platform's strict Pydantic backend crashed with a `500 Internal Server Error` because it forbids extra properties.

**Fix:** Removed invalid fields from the manifest and passed the slug via CLI flag:
```powershell
anna-app dev --slug gitproject-analyzer
```

### Bug #3: The Strict Executa JSON-RPC Protocol
The Python plugin returned a raw JSON dictionary, but Anna rejected it with `tool returned failure (keys=['content'])`. The platform expects a very specific response schema.

**Fix:** Updated the Python backend to return:
```json
{
  "success": true,
  "tool": "build_analyzer_prompt",
  "data": { "prompt": "...", "repo_name": "...", "description": "..." }
}
```
And updated `app.js` to read from `rawFetchResult.data`.

---

## 4. Deep Repository Analysis Feature (Git Clone)

We upgraded the Executa from only fetching GitHub API metadata to actually **cloning the repository locally** and reading source code files. This allows the AI to understand projects even without a README.

### How it works:
1. Uses `git clone --depth 1` (shallow clone) into a `tempfile.TemporaryDirectory()`.
2. Walks the cloned directory with `os.walk()`, filtering out junk directories (`.git`, `node_modules`, `venv`, `__pycache__`, `build`, `dist`).
3. Skips binary files (`.png`, `.jpg`, `.exe`, `.pdf`, `.lock`, etc.).
4. Reads up to **15 source code files** with a **15,000 character safety limit**.
5. Injects the raw source code snippets directly into the LLM prompt.
6. The temporary directory is automatically deleted after extraction.

---

## 5. Fixing the LLM Response in the UI

### Problem: `anna.llm.complete()` returned 502 Bad Gateway
During testing, the Anna platform's LLM routing was temporarily down. We implemented a hack in `app.js` to bypass the LLM and display raw extracted data directly.

### Problem: "No response received" after 502 was fixed
After the Anna team fixed the 502, the UI still showed "No response received" because the LLM response had an unexpected structure. By dumping the raw JSON to the screen, we discovered the actual shape:

```json
{
  "role": "assistant",
  "content": { "type": "text", "text": "...the actual AI response..." },
  "model": "openai/gpt-5-mini",
  "usage": { ... }
}
```

**Fix:** Updated `app.js` to extract the response text correctly:
```javascript
const responseText = llmResult.content?.text || llmResult.text || llmResult.content || "No response received.";
```

---

## 6. Running the App Locally (Development)

### Start the dev server:
```powershell
cd "c:\Users\orailnoor\Documents\gitproject analyzer"
anna-app dev --slug gitproject-analyzer
```
This starts the Anna local development harness, launches the frontend, and connects the Python Executa backend.

### Test the Executa independently (CLI):
```powershell
cd "executas\github-fetcher"
anna-app executa dev --invoke build_analyzer_prompt --args "{`"url`": `"https://github.com/user/repo`"}"
```

### Run the standalone local runner (no Anna needed):
```powershell
.\runner.bat
```
This prompts for a GitHub URL, clones the repo, extracts source code, and optionally calls an LLM API (DeepSeek/OpenAI) directly with your own API key.

---

## 7. Publishing the App to Anna (Complete Step-by-Step)

### Step 1: Publish the Executa (Python backend)

Navigate to the Executa directory and publish it:
```powershell
cd "c:\Users\orailnoor\Documents\gitproject analyzer\executas\github-fetcher"
anna-app executa publish
```

**Output:**
```
✓ executas/github-fetcher: version 0.1.0 frozen
tool_id: tool-orailkane-github-fetcher-khq97duy
```

> **Important:** Note the `tool_id` returned by the server. This is the real production tool_id you must use in `manifest.json`.

> **Note:** We initially tried `anna-app executa publish --publish` (with the `--publish` flag to make it public immediately), but it returned a `500 Internal Server Error`. Publishing without the flag (private) worked fine.

### Step 2: Update `manifest.json` with the real tool_id

Replace the dev `tool_id` in `manifest.json` with the one returned from Step 1:
```json
{
  "required_executas": [
    {
      "tool_id": "tool-orailkane-github-fetcher-khq97duy",
      "min_version": "0.1.0",
      "version": "latest"
    }
  ]
}
```

### Step 3: Push the app (frontend + manifest) to Anna

```powershell
cd "c:\Users\orailnoor\Documents\gitproject analyzer"
anna-app apps push
```

**Output:**
```
✓ bundled:github-fetcher → tool-orailkane-github-fetcher-khq97duy (v0.1.0, unchanged)
✓ working bundle staged (4 files, 8.9 KB)
✓ apps/gitlensanalyzer: working draft updated (rev 1)
```

This uploads your `manifest.json` and the entire `bundle/` folder as a working draft.

### Step 4: Cut an immutable version

```powershell
anna-app apps cut 0.1.0
```

**Output:**
```
✓ apps/gitlensanalyzer: cut immutable version 0.1.0 (version_id=491)
  froze tool-orailkane-github-fetcher-khq97duy → executa_version=346 (v0.1.0)
```

### Step 5: Submit for review

```powershell
anna-app apps submit-review gitlensanalyzer
```

**Output:**
```
✓ apps/gitlensanalyzer: submitted for review
status: pending_review
```

> **Note:** You cannot run `anna-app apps release 0.1.0` until the Anna team approves your app. Once approved, run that command to go live.

### Step 6 (After Approval): Release

```powershell
anna-app apps release 0.1.0
```

---

## 8. Useful Anna CLI Commands Reference

| Command | Description |
|---------|-------------|
| `anna-app dev --slug <slug>` | Start local dev server |
| `anna-app executa dev --invoke <tool> --args <json>` | Test an Executa tool locally |
| `anna-app executa publish` | Upload and freeze an Executa version |
| `anna-app apps push` | Push working draft (manifest + bundle) |
| `anna-app apps cut <version>` | Snapshot draft into immutable version |
| `anna-app apps submit-review <slug>` | Submit app for Anna team review |
| `anna-app apps release <version>` | Make an approved version live |
| `anna-app apps status <slug>` | Check app status |
| `anna-app apps versions <slug>` | List all versions |
| `anna-app apps list` | List all your apps |
| `anna-app executa list` | List all your Executas |

---

## 9. Key Lessons Learned

1. **Never add extra fields to `manifest.json`** — Anna's backend uses strict Pydantic validation and will 500 on unknown keys.
2. **The Executa response schema is NOT standard MCP** — You must return `{ success, tool, data }`, not `{ content: [...] }`.
3. **The `anna.llm.complete()` response nests content** — The AI text is at `result.content.text`, not `result.text`.
4. **PowerShell mangles JSON in CLI args** — Use backtick-escaped quotes: `"{\`"key\`": \`"value\`"}"`.
5. **Use `anna-app executa publish` (without `--publish`)** if the `--publish` flag throws a 500 error. You can make it public later.
6. **Folder names with spaces** cause issues with the CLI auto-slug generator. Always pass `--slug` explicitly.

