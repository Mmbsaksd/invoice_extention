chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.action === "FILL_FORM") {
        chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
            if (tabs[0]) {
                chrome.tabs.sendMessage(tabs[0].id, request, (response) => {
                    const err = chrome.runtime.lastError;
                    if (err) {
                        console.error("Messaging Error:", err.message);
                        sendResponse({ success: false, error: "Script not active. Please REFRESH the page." });
                    } else {
                        sendResponse(response || { success: false, error: "Page did not respond" });
                    }
                });
            } else {
                sendResponse({ success: false, error: "No active tab" });
            }
        });
        return true;
    }
});
