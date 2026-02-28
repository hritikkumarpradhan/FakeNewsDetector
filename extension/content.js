/* 
  content.js 
  Injects "Verify Fact" button onto tweets and fetches text for analysis.
*/

function injectButtons() {
    // Find all tweet articles on Twitter/X
    const tweets = document.querySelectorAll('article[data-testid="tweet"]');

    tweets.forEach(tweet => {
        // Prevent duplicate injections
        if (tweet.querySelector('.truthlens-verify-btn')) return;

        // Find the action buttons bar (Reply, Retweet, Like, Share) to inject alongside
        const actionBar = tweet.querySelector('div[role="group"]');
        if (!actionBar) return;

        // Create the wrapper
        const btnWrapper = document.createElement("div");
        btnWrapper.className = "truthlens-wrapper";

        // Create the button
        const btn = document.createElement("button");
        btn.className = "truthlens-verify-btn";
        btn.innerHTML = `<span class="truthlens-icon">🛡️</span> <span class="truthlens-text">Verify</span>`;

        // Create the result container (hidden initially)
        const resultBox = document.createElement("div");
        resultBox.className = "truthlens-result hidden";

        btn.addEventListener("click", async (e) => {
            e.preventDefault();
            e.stopPropagation();

            // Extract text from the tweet body
            const textDiv = tweet.querySelector('div[data-testid="tweetText"]');
            const tweetText = textDiv ? textDiv.innerText : "";

            if (!tweetText || tweetText.length < 10) {
                alert("TruthLens: Not enough text in this tweet to analyze.");
                return;
            }

            // Show loading state
            btn.innerHTML = `<span class="truthlens-icon">⏳</span> <span class="truthlens-text">Analyzing...</span>`;
            btn.disabled = true;

            // Send to background script
            chrome.runtime.sendMessage({ type: "ANALYZE_TEXT", text: tweetText }, (response) => {
                btn.disabled = false;

                if (response && response.success) {
                    const { label, score, summary_bullets } = response.data;
                    const fakePercent = Math.round(score * 100);

                    let colorClass = "tl-safe";
                    if (fakePercent >= 70) colorClass = "tl-danger";
                    else if (fakePercent > 30) colorClass = "tl-warning";

                    // Inject result UI
                    resultBox.innerHTML = `
            <div class="tl-header ${colorClass}">
              <strong>${label}</strong> (${fakePercent}% Fake)
            </div>
            ${summary_bullets && summary_bullets.length > 0 ? `
              <ul class="tl-summary">
                ${summary_bullets.map(b => `<li>${b}</li>`).join('')}
              </ul>
            ` : ''}
          `;
                    resultBox.classList.remove("hidden");
                    btn.innerHTML = `<span class="truthlens-icon">✅</span> <span class="truthlens-text">Done (Hover to View)</span>`;
                    btn.classList.add("btn-done");
                } else {
                    console.error("TruthLens Error:", response?.error);
                    btn.innerHTML = `<span class="truthlens-icon">❌</span> <span class="truthlens-text">Error</span>`;
                    alert("TruthLens Analysis failed: " + (response?.error || "Unknown error"));
                }
            });
        });

        btnWrapper.appendChild(btn);
        btnWrapper.appendChild(resultBox);

        // Insert just before or at the end of the action bar
        actionBar.appendChild(btnWrapper);
    });
}

// Observe mutations for infinite scrolling
const observer = new MutationObserver((mutations) => {
    let shouldInject = false;
    mutations.forEach(m => {
        if (m.addedNodes.length > 0) shouldInject = true;
    });
    if (shouldInject) {
        injectButtons();
    }
});

// Start observing the body
observer.observe(document.body, { childList: true, subtree: true });

// Initial injection
setTimeout(injectButtons, 2000);
