/* 
  Invoice Assistant - Content Script
  This script runs DIRECTLY inside the webpage (like SAP, Oracle, etc.).
  It waits for a command from the extension, finds the fields, and types the data.
*/

(() => {
    // Listen for the "FILL" command from the extension popup
    chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
        if (request.action === "FILL") {
            const invoiceData = request.data;

            // Define what we are looking for and what labels might name them
            const fieldMap = [
                { key: "supplier", labels: ["Supplier", "Vendor", "Name", "LIFNR"] },
                { key: "invoice_date", labels: ["Invoice Date", "Doc Date", "BLDAT", "Inv Date"] },
                { key: "posting_date", labels: ["Posting Date", "Pstng Date", "BUDAT"] },
                { key: "reference", labels: ["Reference", "Invoice #", "XBLNR", "Doc #"] },
                { key: "amount", labels: ["Amount", "Gross", "WRBTR", "Total"] },
                { key: "tax_amount", labels: ["Tax", "VAT", "WMWST"] }
            ];

            let countFilled = 0;

            // For each piece of data, find the box and fill it
            fieldMap.forEach(field => {
                const element = findTargetElement(field.labels);
                const value = invoiceData[field.key];

                if (element && value) {
                    fillValueIntoElement(element, value);
                    countFilled++;
                }
            });

            console.log(`Invoice Assistant: Filled ${countFilled} fields.`);
            sendResponse({ success: true, filled: countFilled });
        }
    });

    /**
     * Logic to find a text box based on common SAP/Web names or labels next to it.
     */
    function findTargetElement(labels) {
        // Step A: Search for common IDs/Names that contain our label
        // Example: Look for any box with 'id' containing 'Supplier'
        const selector = labels.map(l => `[id*="${l}" i], [name*="${l}" i], [placeholder*="${l}" i]`).join(',');
        const directMatch = document.querySelector(selector);
        if (directMatch && isVisible(directMatch)) return directMatch;

        // Step B: Search for a Label text (like "Name:") and find the input box next to it
        const allInputs = Array.from(document.querySelectorAll('input:not([type="hidden"]), textarea'));
        for (let labelText of labels) {
            // Find a piece of text on the page that matches our label
            const labelElement = Array.from(document.querySelectorAll('label, span, b, div')).find(el =>
                el.innerText.toLowerCase().includes(labelText.toLowerCase()) && el.innerText.length < 30
            );

            if (labelElement) {
                const labelRect = labelElement.getBoundingClientRect();
                // Find an input box that is on the same line as the label
                const nearbyInput = allInputs.find(input => {
                    const inputRect = input.getBoundingClientRect();
                    const isSameLine = Math.abs(labelRect.top - inputRect.top) < 20;
                    const isToTheRight = inputRect.left > labelRect.left;
                    return isSameLine && isToTheRight;
                });
                if (nearbyInput) return nearbyInput;
            }
        }
        return null;
    }

    /**
     * Skillfully injects text into a box so the webpage knows it has changed.
     * (Standard typing often fails on modern websites like React/SAP UI5).
     */
    function fillValueIntoElement(element, value) {
        element.focus();

        // We use a "Descriptor Setter" to bypass website frameworks that might block programmatic typing
        const prototype = element instanceof HTMLTextAreaElement ? window.HTMLTextAreaElement.prototype : window.HTMLInputElement.prototype;
        const setter = Object.getOwnPropertyDescriptor(prototype, 'value')?.set;

        if (setter) {
            setter.call(element, value); // Force the value in
        } else {
            element.value = value; // Fallback to simple method
        }

        // Tell the website "Hey, a human just typed something here!"
        ['input', 'change', 'blur'].forEach(evtName => {
            element.dispatchEvent(new Event(evtName, { bubbles: true }));
        });
    }

    function isVisible(el) {
        const r = el.getBoundingClientRect();
        return r.width > 0 && r.height > 0;
    }
})();
