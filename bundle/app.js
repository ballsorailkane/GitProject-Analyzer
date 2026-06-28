import { AnnaAppRuntime } from "/static/anna-apps/_sdk/latest/index.js";

function parseMarkdown(text) {
  let html = text
    .replace(/^### (.*$)/gim, '<h3>$1</h3>')
    .replace(/^## (.*$)/gim, '<h2>$1</h2>')
    .replace(/^# (.*$)/gim, '<h1>$1</h1>')
    .replace(/\*\*(.*?)\*\*/gim, '<strong>$1</strong>')
    .replace(/\*(.*?)\*/gim, '<em>$1</em>');
    
  html = html.replace(/^\s*\-\s(.*)$/gim, '<ul><li>$1</li></ul>');
  html = html.replace(/<\/ul>\n<ul>/gim, '\n');
  
  html = html.replace(/^\s*\d\.\s(.*)$/gim, '<ol><li>$1</li></ol>');
  html = html.replace(/<\/ol>\n<ol>/gim, '\n');
  
  return html;
}

async function init() {
  const anna = await AnnaAppRuntime.connect();
  
  const input = document.getElementById('repo-url');
  const btn = document.getElementById('analyze-btn');
  const loadingState = document.getElementById('loading-state');
  const loadingText = document.getElementById('loading-text');
  const resultsSection = document.getElementById('results-section');
  const errorSection = document.getElementById('error-section');
  const errorMessage = document.getElementById('error-message');
  
  const repoNameEl = document.getElementById('repo-name');
  const repoDescEl = document.getElementById('repo-description');
  const analysisContentEl = document.getElementById('analysis-content');
  
  btn.addEventListener('click', async () => {
    const url = input.value.trim();
    if (!url) return;
    
    resultsSection.style.display = 'none';
    errorSection.style.display = 'none';
    btn.disabled = true;
    loadingState.style.display = 'block';
    
    try {
      loadingText.textContent = "Fetching repository data (this might take a moment)...";
      
      const toolId = window.__ANNA_TOOL_IDS__ ? window.__ANNA_TOOL_IDS__['github-fetcher'] : 'bundled:github-fetcher';
      
      const rawFetchResult = await anna.tools.invoke({
        tool_id: toolId,
        method: "build_analyzer_prompt",
        args: { url }
      });
      
      const fetchResult = rawFetchResult.data || rawFetchResult;
      
      if (!fetchResult || !fetchResult.prompt) {
        throw new Error("Failed to extract data from repository.");
      }
      
      repoNameEl.textContent = fetchResult.repo_name;
      repoDescEl.textContent = fetchResult.description || "No description provided.";
      
      loadingText.textContent = "Analyzing project with Anna AI...";
      
      const llmResult = await anna.llm.complete({
        messages: [
          {
            role: "user",
            content: fetchResult.prompt
          }
        ]
      });
      
      const responseText = llmResult.message?.content || llmResult.content || llmResult.text || (typeof llmResult === 'string' ? llmResult : JSON.stringify(llmResult));
      analysisContentEl.innerHTML = parseMarkdown(responseText);
      
      loadingState.style.display = 'none';
      resultsSection.style.display = 'block';
      
    } catch (err) {
      console.error(err);
      errorMessage.textContent = err.message || "An error occurred during analysis.";
      loadingState.style.display = 'none';
      errorSection.style.display = 'block';
    } finally {
      btn.disabled = false;
    }
  });
}

init().catch(console.error);
