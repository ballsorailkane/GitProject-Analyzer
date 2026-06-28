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
      
      // --- HACK START ---
      // Since anna.llm.complete is currently returning a 502 Bad Gateway from the platform,
      // we will bypass the LLM entirely and just display the raw data that the Executa successfully fetched!
      const rawExtractedData = fetchResult.prompt
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;");
        
      analysisContentEl.innerHTML = `
        <div style="background: rgba(255, 50, 50, 0.1); padding: 12px; border-radius: 8px; margin-bottom: 16px; border: 1px solid rgba(255,50,50,0.3);">
          <strong>⚠️ Anna LLM API is down (502 Bad Gateway)</strong><br>
          Bypassing AI analysis. Displaying the raw data successfully extracted from GitHub by your Executa:
        </div>
        <pre style="white-space: pre-wrap; font-family: monospace; font-size: 13px; color: #e2e8f0; line-height: 1.5;">${rawExtractedData}</pre>
      `;
      // --- HACK END ---
      
      loadingState.style.display = 'none';
      resultsSection.style.display = 'block';
      
    } catch (err) {
      // Escape HTML to prevent Cloudflare 502 pages from rendering raw HTML
      const safeErrorMessage = err.message
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;");
        
      analysisContentEl.innerHTML = `
        <div style="background: rgba(239, 68, 68, 0.1); border: 1px solid rgba(239, 68, 68, 0.3); padding: 16px; border-radius: 8px; text-align: center;">
          <strong style="color: #ef4444; display: block; margin-bottom: 8px;">Anna Platform Error</strong>
          <p style="color: #e2e8f0; font-size: 14px; margin: 0;">The Anna AI servers are currently down.</p>
          <pre style="margin-top: 12px; padding: 12px; background: rgba(0,0,0,0.3); border-radius: 4px; color: #ef4444; font-size: 12px; text-align: left; overflow-x: auto;">${safeErrorMessage}</pre>
        </div>
      `;
      loadingState.style.display = 'none';
      resultsSection.style.display = 'block';
    } finally {
      btn.disabled = false;
    }
  });
}

init().catch(console.error);
