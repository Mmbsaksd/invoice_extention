chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.action === "FILL_FORM") {
        handleFillRequest(request, sendResponse);
        return true; // Keep channel open
    }
});

async function handleFillRequest(request, sendResponse) {
    try {
        const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
        if (!tab) {
            sendResponse({ success: false, error: "No active tab" });
            return;
        }

        try {
            // Attempt 1: Normal message
            const response = await chrome.tabs.sendMessage(tab.id, request);
            sendResponse(response || { success: false, error: "Empty response" });
        } catch (e) {
            // Attempt 2: Auto-inject and retry if script is missing
            if (e.message.includes("Receiving end does not exist")) {
                console.log("Invoice Assistant: Content script missing. Injecting...");
                await chrome.scripting.executeScript({
                    target: { tabId: tab.id },
                    files: ["selector.js", "content_script/content.js"]
                });

                // Small delay for script initialization
                await new Promise(r => setTimeout(r, 100));

                const response = await chrome.tabs.sendMessage(tab.id, request);
                sendResponse(response || { success: false, error: "Injection failed" });
            } else {
                throw e;
            }
        }
    } catch (err) {
        console.error("Messaging Pipeline Error:", err);
        sendResponse({ success: false, error: err.message });
    }
}
