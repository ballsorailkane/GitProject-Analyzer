import sys
from github_fetcher import (
    parse_repo_url, fetch_repo_data, fetch_languages, 
    fetch_tree, fetch_readme, clone_and_read_repo, build_prompt
)

def main():
    print("="*50)
    print(" GitHub Local Repository Analyzer")
    print("="*50)
    
    url = input("\nEnter GitHub Repo URL: ").strip()
    if not url:
        print("URL cannot be empty.")
        return

    print(f"\n[1/3] Parsing URL...")
    owner, repo = parse_repo_url(url)
    if not owner or not repo:
        print("Invalid GitHub URL format.")
        return

    try:
        print(f"[2/3] Fetching metadata for {owner}/{repo} from GitHub API...")
        repo_data = fetch_repo_data(owner, repo)
        languages = fetch_languages(owner, repo)
        branch = repo_data.get("default_branch", "main")
        tree = fetch_tree(owner, repo, branch)
        readme = fetch_readme(owner, repo)
        
        print(f"[3/3] Cloning repository locally to extract source code (this might take a few seconds)...")
        local_context = clone_and_read_repo(url)
        
        prompt = build_prompt(repo_data, languages, tree, readme, local_context)
        
        print("\n" + "="*60)
        print("✅ ANALYSIS CONTEXT EXTRACTED SUCCESSFULLY")
        print("="*60 + "\n")
        
        # Ask if they want to run it through an LLM
        api_key = input("\nDo you want to generate an AI explanation? Enter an OpenAI/DeepSeek API Key (or press Enter to just view the raw data): ").strip()
        
        if api_key:
            print("\n🤖 Asking AI to analyze the repository...\n")
            
            # Auto-detect endpoint (default to OpenAI if it looks like an OpenAI key, else assume DeepSeek for this user)
            endpoint = "https://api.openai.com/v1/chat/completions" if api_key.startswith("sk-proj") else "https://api.deepseek.com/chat/completions"
            model = "gpt-4o-mini" if api_key.startswith("sk-proj") else "deepseek-chat"
            
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": model,
                "messages": [{"role": "user", "content": prompt}]
            }
            
            response = requests.post(endpoint, headers=headers, json=payload)
            if response.status_code == 200:
                print(response.json()["choices"][0]["message"]["content"])
            else:
                print(f"❌ LLM API Error ({response.status_code}): {response.text}")
                print("\nHere is the raw prompt instead:\n\n" + prompt)
        else:
            print(prompt)
            
        print("\n" + "="*60)
        
    except Exception as e:
        print(f"\n❌ Error: {e}")

if __name__ == "__main__":
    main()
