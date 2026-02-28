document.addEventListener("DOMContentLoaded", () => {
    const btn = document.getElementById("analyzeBtn");
    const resultDiv = document.getElementById("result");
    const scoreBanner = document.getElementById("scoreBanner");
    const summaryList = document.getElementById("summaryList");
    const errorDiv = document.getElementById("error");

    btn.addEventListener("click", async () => {
        // Hide UI
        resultDiv.style.display = "none";
        errorDiv.style.display = "none";
        btn.disabled = true;
        btn.textContent = "Analyzing Page...";

        try {
            // Get active tab URL
            const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
            if (!tab || !tab.url) throw new Error("Could not find active tab URL.");

            // Check if URL is valid for scraping (not chrome:// etc)
            if (!tab.url.startsWith("http")) {
                throw new Error("Cannot analyze this type of page. Please open a real news article.");
            }

            // We send the URL to the backend, the backend scraper will fetch and analyze it
            const response = await fetch("http://127.0.0.1:8000/api/analyze", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ url: tab.url })
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.detail || "Analysis failed on the server.");
            }

            // Display results
            const fakePercent = Math.round(data.score * 100);
            let colorClass = "tl-safe";
            if (fakePercent >= 70) colorClass = "tl-danger";
            else if (fakePercent > 30) colorClass = "tl-warning";

            scoreBanner.className = `score-banner ${colorClass}`;
            scoreBanner.textContent = `${data.label} (${fakePercent}% Fake)`;

            if (data.summary_bullets && data.summary_bullets.length > 0) {
                summaryList.innerHTML = data.summary_bullets
                    .map(b => `<li>${b}</li>`)
                    .join('');
            } else {
                summaryList.innerHTML = "<li>No summary available for this content.</li>";
            }

            resultDiv.style.display = "block";
        } catch (err) {
            errorDiv.textContent = err.message || "An unexpected error occurred.";
            errorDiv.style.display = "block";
        } finally {
            btn.disabled = false;
            btn.textContent = "Analyze Current Page";
        }
    });
});
