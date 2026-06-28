import os
import re
import sys
import json
import textwrap
import requests

# ============================================================
#  ANSI color helpers
# ============================================================

class C:
    RESET   = "\033[0m"
    BOLD    = "\033[1m"
    DIM     = "\033[2m"
    UL      = "\033[4m"
    CYAN    = "\033[36m"
    GREEN   = "\033[32m"
    YELLOW  = "\033[33m"
    MAGENTA = "\033[35m"
    RED     = "\033[31m"
    BLUE    = "\033[34m"
    WHITE   = "\033[37m"
    GRAY    = "\033[90m"


def styled(text, *styles):
    return "".join(styles) + str(text) + C.RESET


def hr(char="-", length=60):
    print(styled(char * length, C.DIM))


def heading(text):
    print()
    hr("=")
    print(styled("  " + text, C.BOLD, C.CYAN))
    hr("=")


def subheading(text):
    print()
    print(styled(">> " + text, C.BOLD, C.YELLOW))
    hr("-", 40)


def label(key, value):
    print(styled("  " + key + ": ", C.BOLD, C.WHITE) + styled(value, C.DIM))


def bullet(text):
    print(styled("  - ", C.GREEN) + text)


def code_block(lines):
    width = 56
    print(styled("  +" + "-" * width + "+", C.DIM))
    for line in lines:
        padded = line[:width].ljust(width)
        print(styled("  | ", C.DIM) + styled(padded, C.GREEN) + styled("|", C.DIM))
    print(styled("  +" + "-" * width + "+", C.DIM))


def numbered_step(n, title, description=None, commands=None):
    print()
    print(styled(f"  [Step {n}] ", C.BOLD, C.MAGENTA) + styled(title, C.BOLD, C.WHITE))
    if description:
        print(styled("    " + description, C.DIM))
    if commands:
        for cmd in commands:
            print(styled("    $ ", C.YELLOW) + styled(cmd, C.GREEN))


def print_wrapped(text, indent=4, width=76):
    """Print text with word-wrapping."""
    prefix = " " * indent
    for paragraph in text.split("\n"):
        paragraph = paragraph.strip()
        if not paragraph:
            print()
            continue
        if paragraph.startswith("```"):
            print(styled(prefix + paragraph, C.GREEN))
            continue
        if paragraph.startswith("#"):
            print()
            print(styled(prefix + paragraph.lstrip("# "), C.BOLD, C.CYAN))
            continue
        if paragraph.startswith("- ") or paragraph.startswith("* "):
            print(styled(prefix + "- ", C.GREEN) + paragraph[2:])
            continue
        wrapped = textwrap.fill(paragraph, width=width, initial_indent=prefix, subsequent_indent=prefix)
        print(styled(wrapped, C.DIM))


# ============================================================
#  Config management  (saves API keys to config.json)
# ============================================================

CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")

PROVIDERS = {
    "1": {
        "name": "OpenRouter",
        "key_env": "OPENROUTER_API_KEY",
        "url": "https://openrouter.ai/api/v1/chat/completions",
        "model": "deepseek/deepseek-chat-v3-0324:free",
        "format": "openai",
    },
    "2": {
        "name": "Google Gemini",
        "key_env": "GEMINI_API_KEY",
        "url": "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent",
        "model": "gemini-2.0-flash",
        "format": "gemini",
    },
    "3": {
        "name": "DeepSeek",
        "key_env": "DEEPSEEK_API_KEY",
        "url": "https://api.deepseek.com/v1/chat/completions",
        "model": "deepseek-chat",
        "format": "openai",
    },
}


def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def save_config(config):
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)


def setup_provider():
    """Interactive provider selection and API key setup."""
    config = load_config()

    print()
    print(styled("  Select your AI provider:", C.BOLD, C.WHITE))
    print()
    for key, prov in PROVIDERS.items():
        saved = config.get(prov["key_env"])
        status = styled(" [key saved]", C.GREEN) if saved else ""
        print(f"    {styled(key, C.BOLD, C.CYAN)}) {prov['name']}{status}")
    print()

    choice = input(styled("  Enter choice (1/2/3): ", C.WHITE)).strip()
    if choice not in PROVIDERS:
        print(styled("  Invalid choice.", C.RED))
        return None, None

    provider = PROVIDERS[choice]
    api_key = config.get(provider["key_env"]) or os.environ.get(provider["key_env"])

    if api_key:
        masked = api_key[:6] + "..." + api_key[-4:]
        print(styled(f"  Using saved key: {masked}", C.DIM))
        use_saved = input(styled("  Use this key? (Y/n): ", C.WHITE)).strip().lower()
        if use_saved in ("n", "no"):
            api_key = None

    if not api_key:
        api_key = input(styled(f"  Enter your {provider['name']} API key: ", C.WHITE)).strip()
        if not api_key:
            print(styled("  No API key provided.", C.RED))
            return None, None

        save_it = input(styled("  Save key for future use? (Y/n): ", C.WHITE)).strip().lower()
        if save_it not in ("n", "no"):
            config[provider["key_env"]] = api_key
            save_config(config)
            print(styled("  Key saved to config.json", C.GREEN))

    return provider, api_key


# ============================================================
#  GitHub API helpers
# ============================================================

GITHUB_HEADERS = {
    "User-Agent": "GitProject-Analyzer-CLI/2.0",
    "Accept": "application/vnd.github.v3+json",
}


def parse_repo_url(url_input):
    url_input = url_input.strip().rstrip("/")
    match = re.match(r"(?:https?://)?(?:www\.)?github\.com/([^/]+)/([^/]+)", url_input)
    if match:
        return match.group(1), match.group(2).replace(".git", "")
    match = re.match(r"^([^/\s]+)/([^/\s]+)$", url_input)
    if match:
        return match.group(1), match.group(2)
    return None, None


def fetch_repo_data(owner, repo):
    """Fetch repository metadata from GitHub API."""
    url = f"https://api.github.com/repos/{owner}/{repo}"
    resp = requests.get(url, headers=GITHUB_HEADERS, timeout=15)
    resp.raise_for_status()
    return resp.json()


def fetch_languages(owner, repo):
    url = f"https://api.github.com/repos/{owner}/{repo}/languages"
    try:
        resp = requests.get(url, headers=GITHUB_HEADERS, timeout=15)
        resp.raise_for_status()
        return resp.json()
    except Exception:
        return {}


def fetch_tree(owner, repo, branch="main"):
    url = f"https://api.github.com/repos/{owner}/{repo}/git/trees/{branch}"
    try:
        resp = requests.get(url, headers=GITHUB_HEADERS, timeout=15)
        resp.raise_for_status()
        return resp.json().get("tree", [])
    except Exception:
        return []


def fetch_readme(owner, repo):
    url = f"https://api.github.com/repos/{owner}/{repo}/readme"
    headers = {**GITHUB_HEADERS, "Accept": "application/vnd.github.v3.raw"}
    try:
        resp = requests.get(url, headers=headers, timeout=15)
        if resp.status_code == 200:
            return resp.text
    except Exception:
        pass
    return None


def format_num(n):
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.1f}K"
    return str(n)


# ============================================================
#  AI provider calls
# ============================================================

def call_ai(provider, api_key, prompt):
    """Send a prompt to the selected AI provider and return the response text."""

    if provider["format"] == "openai":
        # Works for both OpenRouter and DeepSeek
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        # OpenRouter-specific headers
        if "openrouter" in provider["url"]:
            headers["HTTP-Referer"] = "https://github.com/gitlens-analyzer"
            headers["X-Title"] = "GitLens Analyzer"

        payload = {
            "model": provider["model"],
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are a senior software engineer who explains open-source projects clearly. "
                        "You provide concise, accurate explanations and actionable setup instructions. "
                        "Use plain text formatting. Use markdown headings (#) and bullet points (-) for structure. "
                        "Do not use emojis."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            "max_tokens": 3000,
            "temperature": 0.3,
        }

        resp = requests.post(provider["url"], headers=headers, json=payload, timeout=60)
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]

    elif provider["format"] == "gemini":
        url = f"{provider['url']}?key={api_key}"
        payload = {
            "contents": [
                {
                    "parts": [
                        {
                            "text": (
                                "You are a senior software engineer who explains open-source projects clearly. "
                                "You provide concise, accurate explanations and actionable setup instructions. "
                                "Use plain text formatting. Use markdown headings (#) and bullet points (-) for structure. "
                                "Do not use emojis.\n\n"
                                + prompt
                            )
                        }
                    ]
                }
            ],
            "generationConfig": {
                "maxOutputTokens": 3000,
                "temperature": 0.3,
            },
        }

        resp = requests.post(url, json=payload, timeout=60)
        resp.raise_for_status()
        data = resp.json()
        return data["candidates"][0]["content"]["parts"][0]["text"]

    else:
        raise ValueError(f"Unknown provider format: {provider['format']}")


# ============================================================
#  Build the analysis prompt
# ============================================================

def build_prompt(repo_data, languages, tree, readme):
    """Build a comprehensive prompt for the AI model."""

    # Top-level file list
    top_files = [t["path"] for t in tree if "/" not in t["path"]][:30]
    file_list = "\n".join(f"  - {f}" for f in top_files) if top_files else "  (not available)"

    # Language breakdown
    lang_entries = list(languages.items())
    total_bytes = sum(b for _, b in lang_entries) or 1
    lang_text = "\n".join(
        f"  - {lang}: {bytes_val / total_bytes * 100:.1f}%"
        for lang, bytes_val in lang_entries
    ) if lang_entries else "  (not available)"

    # Truncate README to avoid token limits
    readme_text = readme[:6000] if readme else "(no README found)"

    prompt = f"""Analyze the following open-source GitHub repository and provide a detailed but concise breakdown.

## Repository Metadata
- Name: {repo_data.get('name', 'N/A')}
- Full Name: {repo_data.get('full_name', 'N/A')}
- Description: {repo_data.get('description', 'No description')}
- Primary Language: {repo_data.get('language', 'Unknown')}
- Stars: {format_num(repo_data.get('stargazers_count', 0))}
- Forks: {format_num(repo_data.get('forks_count', 0))}
- License: {repo_data.get('license', {}).get('name', 'Not specified') if repo_data.get('license') else 'Not specified'}
- Topics: {', '.join(repo_data.get('topics', [])) or 'None'}
- Created: {repo_data.get('created_at', 'N/A')[:10]}
- Last Updated: {repo_data.get('updated_at', 'N/A')[:10]}

## Languages
{lang_text}

## Top-Level Files/Directories
{file_list}

## README Content
{readme_text}

---

Please provide your analysis in the following sections:

# Project Explanation
Explain what this project is, what problem it solves, who it is for, and why someone might use it. Be specific about its key features and use cases.

# Architecture Overview
Briefly describe the project architecture and how the codebase is organized based on the file structure.

# Prerequisites
List any software, tools, or accounts needed before setting up this project.

# Step-by-Step Setup Guide
Provide clear, numbered steps to clone, install, configure, and run this project locally. Include exact terminal commands. If there are environment variables or config files needed, mention them.

# Common Issues and Tips
List 2-3 common issues a new developer might face when setting up this project and how to resolve them.
"""
    return prompt


# ============================================================
#  Display functions
# ============================================================

def display_repo_info(repo_data, languages, tree):
    """Display the raw repository metadata in the terminal."""

    subheading("Project Overview")
    label("Name", repo_data.get("name", "N/A"))
    label("Full Name", repo_data.get("full_name", "N/A"))
    label("Description", repo_data.get("description") or "No description provided")
    label("URL", repo_data.get("html_url", "N/A"))
    label("Default Branch", repo_data.get("default_branch", "main"))
    lic = repo_data.get("license")
    label("License", lic["name"] if lic else "Not specified")
    label("Created", repo_data.get("created_at", "N/A")[:10])
    label("Last Updated", repo_data.get("updated_at", "N/A")[:10])
    label("Stars", format_num(repo_data.get("stargazers_count", 0)))
    label("Forks", format_num(repo_data.get("forks_count", 0)))
    label("Open Issues", format_num(repo_data.get("open_issues_count", 0)))
    label("Size", f"{repo_data.get('size', 0) / 1024:.1f} MB")
    topics = repo_data.get("topics", [])
    if topics:
        label("Topics", ", ".join(topics))

    # Languages
    subheading("Tech Stack")
    lang_entries = list(languages.items())
    if lang_entries:
        total = sum(b for _, b in lang_entries) or 1
        print()
        for lang, bytes_val in lang_entries:
            pct = bytes_val / total * 100
            bar_len = max(1, round(pct / 100 * 30))
            bar = "#" * bar_len + "." * (30 - bar_len)
            print(
                styled(f"  {lang:<18}", C.BOLD, C.WHITE)
                + styled(bar + " ", C.CYAN)
                + styled(f"{pct:.1f}%", C.DIM)
            )
    else:
        print(styled("  No language data available.", C.DIM))

    # File tree
    subheading("Project Structure")
    print()
    top_level = [t for t in tree if "/" not in t["path"]][:30]
    for i, item in enumerate(top_level):
        is_last = i == len(top_level) - 1
        prefix = "  +-- " if is_last else "  |-- "
        icon = "[dir]  " if item["type"] == "tree" else "[file] "
        color = C.YELLOW if item["type"] == "tree" else C.DIM
        print(styled(prefix, C.DIM) + styled(icon, color) + styled(item["path"], C.WHITE))


def display_ai_analysis(analysis_text):
    """Display the AI-generated analysis with formatting."""
    subheading("AI-Powered Analysis")
    print()
    print_wrapped(analysis_text)


# ============================================================
#  Main
# ============================================================

def analyze(owner, repo, provider, api_key):
    heading("GitLens Analyzer")
    print(styled(f"  Analyzing: {owner}/{repo}", C.DIM))
    print()

    # Step 1: Fetch repo data
    sys.stdout.write(styled("  [1/5] Fetching repository metadata...", C.DIM))
    sys.stdout.flush()
    try:
        repo_data = fetch_repo_data(owner, repo)
        print(styled(" done", C.GREEN))
    except requests.HTTPError as e:
        print(styled(" FAILED", C.RED))
        if e.response.status_code == 404:
            print(styled("  Repository not found. Check the URL and try again.", C.RED))
        else:
            print(styled(f"  Error: {e}", C.RED))
        return
    except Exception as e:
        print(styled(f" FAILED - {e}", C.RED))
        return

    # Step 2: Fetch languages
    sys.stdout.write(styled("  [2/5] Fetching language breakdown...", C.DIM))
    sys.stdout.flush()
    languages = fetch_languages(owner, repo)
    print(styled(" done", C.GREEN))

    # Step 3: Fetch tree
    sys.stdout.write(styled("  [3/5] Fetching project structure...", C.DIM))
    sys.stdout.flush()
    branch = repo_data.get("default_branch", "main")
    tree = fetch_tree(owner, repo, branch)
    print(styled(" done", C.GREEN))

    # Step 4: Fetch README
    sys.stdout.write(styled("  [4/5] Fetching README...", C.DIM))
    sys.stdout.flush()
    readme = fetch_readme(owner, repo)
    print(styled(" done" if readme else " not found", C.GREEN if readme else C.YELLOW))

    # Step 5: AI analysis
    sys.stdout.write(styled(f"  [5/5] Generating analysis via {provider['name']}...", C.DIM))
    sys.stdout.flush()
    try:
        prompt = build_prompt(repo_data, languages, tree, readme)
        ai_response = call_ai(provider, api_key, prompt)
        print(styled(" done", C.GREEN))
    except requests.HTTPError as e:
        print(styled(" FAILED", C.RED))
        try:
            err_body = e.response.json()
            err_msg = err_body.get("error", {}).get("message", str(e))
        except Exception:
            err_msg = str(e)
        print(styled(f"  AI API Error: {err_msg}", C.RED))
        print(styled("  Showing repository data without AI analysis.", C.YELLOW))
        ai_response = None
    except Exception as e:
        print(styled(f" FAILED - {e}", C.RED))
        print(styled("  Showing repository data without AI analysis.", C.YELLOW))
        ai_response = None

    # Display results
    display_repo_info(repo_data, languages, tree)

    if ai_response:
        display_ai_analysis(ai_response)
    else:
        print()
        print(styled("  (AI analysis unavailable -- check your API key and try again)", C.YELLOW))

    # Done
    print()
    hr("=")
    print(
        styled("  Analysis complete for ", C.DIM)
        + styled(repo_data["full_name"], C.BOLD, C.CYAN)
    )
    hr("=")
    print()


def main():
    os.system("cls" if os.name == "nt" else "clear")
    print()
    print(styled("  +------------------------------------------------+", C.CYAN))
    print(styled("  |", C.CYAN) + styled("        GitLens Analyzer  v2.0                ", C.BOLD, C.WHITE) + styled("|", C.CYAN))
    print(styled("  |", C.CYAN) + styled("   Open Source Project Explorer (Terminal)     ", C.DIM) + styled("|", C.CYAN))
    print(styled("  |", C.CYAN) + styled("   Powered by AI  (OpenRouter/Gemini/DeepSeek)", C.DIM) + styled("|", C.CYAN))
    print(styled("  +------------------------------------------------+", C.CYAN))

    # Provider setup
    provider, api_key = setup_provider()
    if not provider:
        print(styled("  Exiting.", C.DIM))
        sys.exit(1)

    print()
    print(styled(f"  Using: {provider['name']} ({provider['model']})", C.GREEN))
    hr("-", 50)

    # Main loop
    while True:
        print()
        url_input = input(
            styled("  Enter GitHub repo URL ", C.WHITE)
            + styled("(or 'quit' to exit)", C.DIM)
            + styled(": ", C.WHITE)
        ).strip()

        if url_input.lower() in ("quit", "exit", "q"):
            print()
            print(styled("  Goodbye!", C.DIM))
            print()
            break

        owner, repo = parse_repo_url(url_input)
        if not owner:
            print(styled("  Invalid input. Use a GitHub URL or owner/repo format.", C.RED))
            print(styled("  Examples: https://github.com/facebook/react  or  facebook/react", C.DIM))
            continue

        print()
        analyze(owner, repo, provider, api_key)


if __name__ == "__main__":
    main()
