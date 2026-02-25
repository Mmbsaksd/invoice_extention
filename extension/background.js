chrome.runtime.onMessage.addListener((req, sender, sendResponse) => {
    if (req.action === "FILL") {
        fillForm(req.data).then(sendResponse);
        return true;
    }
});

async function fillForm(data) {
    try {
        const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
        if (!tab) return { success: false, error: "No tab" };

        // Ensure script is present
        await chrome.scripting.executeScript({
            target: { tabId: tab.id },
            files: ["content.js"]
        }).catch(() => { }); // Already there or error, it's fine

        return await chrome.tabs.sendMessage(tab.id, req);
    } catch (e) {
        return { success: false, error: e.message };
    }
}

// Fixed background script to simple relay
chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
    if (msg.action === "FILL") {
        chrome.tabs.query({ active: true, currentWindow: true }, tabs => {
            chrome.tabs.sendMessage(tabs[0].id, msg, sendResponse);
        });
        return true;
    }
});
