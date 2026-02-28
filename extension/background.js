/* Background Service Worker for TruthLens */

// Forward requests to the local backend to bypass CORS inside content scripts
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.type === "ANALYZE_TEXT") {
        // Fire and forget, or handle async manually for MV3
        fetchAnalysis(request.text)
            .then(data => sendResponse({ success: true, data }))
            .catch(err => sendResponse({ success: false, error: err.message }));

        return true; // Keep message channel open for async response
    }
});

async function fetchAnalysis(text) {
    const response = await fetch("http://127.0.0.1:8000/api/analyze", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({ text })
    });

    if (!response.ok) {
        const err = await response.json();
        throw new Error(err.detail || "Analysis failed");
    }

    return response.json();
}
