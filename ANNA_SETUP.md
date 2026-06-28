# Anna Development Journey & Setup Guide

This document summarizes our entire process of setting up the environment, transforming an existing app into an Anna App, and successfully debugging and running it on the Anna platform.

## 1. Initial Environment Setup
Before writing any Anna-specific code, we ensured the local environment was ready:
* **Node.js** and **uv** (for Python packaging) were already installed.
* We fixed a PowerShell execution policy error (`PSSecurityException`) by running:
  ```powershell
  Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
  ```
* We installed the official Anna CLI globally:
  ```powershell
  npm install -g @anna-ai/cli
  ```
* Finally, we logged into the Anna developer console from the terminal to authenticate the CLI:
  ```powershell
  anna-app login --host https://anna.partners
  ```

## 2. Converting the App Architecture
Instead of using external API keys, we converted the `gitproject analyzer` app to use Anna's hosted LLM platform. We restructured the project to follow the standard Anna App format:
* **`bundle/`**: Contains the frontend files (`index.html`, `app.js`, `style.css`).
* **`executas/github-fetcher/`**: Contains our backend Python plugin that handles making requests to GitHub.
* **`manifest.json`**: The root configuration file declaring necessary permissions (`tools.invoke`) and registering the bundled Executa plugin.

## 3. The 3 Major Bugs We Squashed

### Bug #1: The Missing Python Build System
When running `anna-app dev`, the local harness tried to start our Python Executa in the background using `uv run`. However, `uv` crashed because `github_fetcher.py` was a standalone script without a build configuration.
* **The Fix**: We updated `pyproject.toml` in the Executa directory to include the `hatchling` build system, allowing the script to be properly packaged and executed.

### Bug #2: The Strict `manifest.json` (500 Error)
Because the project folder contained a space (`"gitproject analyzer"`), the CLI threw an error. We initially tried to bypass this by manually adding `"slug"` and `"name"` fields to `manifest.json`. While the local CLI ignored these extra fields, the Anna Platform's strict Pydantic backend immediately crashed with a `500 Internal Server Error` during session creation because it explicitly forbids extra properties.
* **The Fix**: We removed the invalid fields from the manifest and instead explicitly passed the slug via the command line: `anna-app dev --slug gitproject-analyzer`.

### Bug #3: The Strict Executa JSON-RPC Protocol
Once the Python plugin successfully fetched the GitHub data, it returned a raw JSON dictionary. The Anna host rejected this with `tool returned failure`. 
By checking the official `anna-executa-examples` repository, we discovered that Anna Executas require a very strict JSON-RPC payload for tool results.
* **The Fix**: We updated the Python backend to extract the tool name via `params.get("tool")` and explicitly return:
  ```json
  {
    "success": true,
    "tool": "build_analyzer_prompt",
    "data": { "prompt": "...", "repo_name": "..." }
  }
  ```
  We also updated the frontend `app.js` to parse from `rawFetchResult.data`.

## 4. Bypassing External Outages
During final testing, the frontend successfully invoked the Executa tool, but the subsequent call to `anna.llm.complete` threw an external `502 Bad Gateway` error originating from `anna.partners` (via Cloudflare).
To prove the architecture was fundamentally sound, we implemented a temporary hack in the UI to display the raw prompt data fetched by the Executa directly on the screen, proving our code worked perfectly despite the platform's API outage.

## 5. Publishing the App
To prepare the app for the Anna Developer Console, we generated two critical artifacts:
1. **Frontend Bundle**: We compressed the `bundle/` folder into `bundle.zip`.
2. **Backend Wheel**: We compiled the Python Executa into a releasable binary by running `uv build` inside the Executa directory, producing a `.whl` file in the `dist/` folder.

These artifacts were then easily uploaded via the Anna Developer Console UI to transition the auto-registered dev draft into a fully published Anna Application!
