chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.action === "FILL_FORM") {
        try {
            const data = request.data;
            const mapping = [
                ["Supplier", data.supplier],
                ["Invoice date", data.invoice_date],
                ["Posting Date", data.posting_date],
                ["Reference", data.reference],
                ["Amount", data.amount],
                ["Tax Amount", data.tax_amount]
            ];

            let filledCount = 0;
            mapping.forEach(([label, value]) => {
                if (value) {
                    const result = selectorLogic([label, "text"]);
                    if (result.status === "OK") {
                        injectValue(result.element, value);
                        filledCount++;
                    }
                }
            });

            sendResponse({ success: true, filled: filledCount });
        } catch (e) {
            sendResponse({ success: false, error: e.message });
        }
    }
});

function injectValue(el, val) {
    try {
        const isInput = el instanceof HTMLInputElement || el instanceof HTMLTextAreaElement;
        if (isInput) {
            const proto = el instanceof HTMLTextAreaElement ? window.HTMLTextAreaElement.prototype : window.HTMLInputElement.prototype;
            const setter = Object.getOwnPropertyDescriptor(proto, 'value').set;
            setter.call(el, val);
        } else {
            el.innerText = val;
        }
        ['input', 'change', 'blur'].forEach(ev => el.dispatchEvent(new Event(ev, { bubbles: true })));
    } catch (e) {
        el.value = val;
        el.dispatchEvent(new Event('input', { bubbles: true }));
    }
}
