/* 
  Invoice Assistant - Background Script
  This script runs in the background of Chrome. 
  Its job is to take messages from the POPUP and send them to the WEBPAGE.
*/

// Listen for messages from popup.js
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {

    // When the popup asks to "FILL" a form...
    if (request.action === "FILL") {

        // 1. Find the tab the user is currently looking at
        chrome.tabs.query({ active: true, currentWindow: true }, async (tabs) => {
            if (!tabs[0]) return;

            const activeTabId = tabs[0].id;

            try {
                // 2. Ensure our "Content Script" is actually running on that page
                // We "inject" it just in case the page hasn't loaded it yet
                await chrome.scripting.executeScript({
                    target: { tabId: activeTabId },
                    files: ["content.js"]
                });

                // 3. Send the data to content.js on that specific page
                chrome.tabs.sendMessage(activeTabId, request, (response) => {
                    // Send the webpage's answer back to the popup
                    sendResponse(response);
                });

            } catch (err) {
                console.error("Failed to communicate with page:", err);
                sendResponse({ success: false, error: "Is the page fully loaded?" });
            }
        });

        return true; // Keep the communication line open for the response
    }
});
