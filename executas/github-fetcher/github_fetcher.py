import sys
import json
import re
import requests

GITHUB_HEADERS = {
    "User-Agent": "GitProject-Analyzer-AnnaApp/1.0",
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

def build_prompt(repo_data, languages, tree, readme):
    top_files = [t["path"] for t in tree if "/" not in t["path"]][:30]
    file_list = "\n".join(f"  - {f}" for f in top_files) if top_files else "  (not available)"

    lang_entries = list(languages.items())
    total_bytes = sum(b for _, b in lang_entries) or 1
    lang_text = "\n".join(
        f"  - {lang}: {bytes_val / total_bytes * 100:.1f}%"
        for lang, bytes_val in lang_entries
    ) if lang_entries else "  (not available)"

    readme_text = readme[:6000] if readme else "(no README found)"

    prompt = f"""Analyze the following open-source project and provide a clear, concise guide for a developer.

# Repository Metadata
- Name: {repo_data.get('full_name')}
- Description: {repo_data.get('description', 'N/A')}
- Default Branch: {repo_data.get('default_branch', 'main')}
- Stars: {repo_data.get('stargazers_count', 0)}
- License: {repo_data.get('license', {}).get('name', 'Not specified') if repo_data.get('license') else 'Not specified'}

# Language Breakdown
{lang_text}

# Top-level Files (max 30)
{file_list}

# README Context (truncated)
{readme_text}

Please provide:
1. **Architecture Overview**: Briefly describe the project architecture based on the file structure.
2. **Prerequisites**: List any software/tools needed before setting up this project.
3. **Step-by-Step Setup Guide**: Provide clear, numbered steps to clone, install, configure, and run this project locally.
4. **Common Issues and Tips**: List 2-3 common issues a new developer might face and how to resolve them.
"""
    return prompt

def handle_request(req):
    method = req.get("method")
    if method == "describe" or method == "initialize":
        return {
            "capabilities": {},
            "tools": [
                {"name": "build_analyzer_prompt"}
            ]
        }
    elif method == "invoke" or method == "call":
        params = req.get("params", {})
        tool_name = params.get("tool") or params.get("name") or params.get("method")
        
        if tool_name == "build_analyzer_prompt":
            args = params.get("arguments") or params.get("args", {})
            url = args.get("url")
            if not url:
                raise ValueError("URL is required")
            
            owner, repo = parse_repo_url(url)
            if not owner or not repo:
                raise ValueError("Invalid GitHub URL format")
            
            repo_data = fetch_repo_data(owner, repo)
            languages = fetch_languages(owner, repo)
            branch = repo_data.get("default_branch", "main")
            tree = fetch_tree(owner, repo, branch)
            readme = fetch_readme(owner, repo)
            
            prompt = build_prompt(repo_data, languages, tree, readme)
            
            result_dict = {
                "prompt": prompt,
                "repo_name": repo_data.get("full_name"),
                "description": repo_data.get("description")
            }
            return {
                "success": True,
                "tool": tool_name,
                "data": result_dict
            }
        else:
            raise ValueError(f"Unknown tool method: {tool_name}, params: {params}")
    return {}

def main():
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
            req_id = req.get("id")
            try:
                result = handle_request(req)
                resp = {"jsonrpc": "2.0", "id": req_id, "result": result}
            except Exception as e:
                resp = {"jsonrpc": "2.0", "id": req_id, "error": {"code": -32000, "message": str(e)}}
            
            print(json.dumps(resp), flush=True)
        except Exception as e:
            pass # ignore malformed json

if __name__ == "__main__":
    main()
