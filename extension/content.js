// Merged Content Script: Search & Fill
(() => {
    chrome.runtime.onMessage.addListener((req, sender, sendResponse) => {
        if (req.action === "FILL") {
            const data = req.data;
            const fields = [
                { k: "supplier", l: ["Supplier", "Vendor", "Name", "LIFNR"] },
                { k: "invoice_date", l: ["Invoice Date", "Doc Date", "BLDAT"] },
                { k: "posting_date", l: ["Posting Date", "Pstng Date", "BUDAT"] },
                { k: "reference", l: ["Reference", "Invoice #", "XBLNR"] },
                { k: "amount", l: ["Amount", "Gross", "WRBTR"] },
                { k: "tax_amount", l: ["Tax", "VAT", "WMWST"] }
            ];

            let filled = 0;
            fields.forEach(f => {
                const el = findField(f.l);
                if (el && data[f.k]) {
                    inject(el, data[f.k]);
                    filled++;
                }
            });
            sendResponse({ success: true, filled });
        }
    });

    function findField(labels) {
        // 1. Direct match
        const sel = labels.map(l => `[id*="${l}" i], [name*="${l}" i], [placeholder*="${l}" i]`).join(',');
        const direct = document.querySelector(sel);
        if (direct && isVisible(direct)) return direct;

        // 2. Proximity/Label match
        const inputs = Array.from(document.querySelectorAll('input:not([type="hidden"]), textarea'));
        for (let l of labels) {
            const lEl = Array.from(document.querySelectorAll('label, span, b, div')).find(e =>
                e.innerText.toLowerCase().includes(l.toLowerCase()) && e.innerText.length < 30
            );
            if (lEl) {
                const rect = lEl.getBoundingClientRect();
                const nearby = inputs.find(i => {
                    const iRect = i.getBoundingClientRect();
                    return Math.abs(rect.top - iRect.top) < 20 && iRect.left > rect.left;
                });
                if (nearby) return nearby;
            }
        }
        return null;
    }

    function inject(el, val) {
        el.focus();
        const setter = Object.getOwnPropertyDescriptor(el instanceof HTMLTextAreaElement ? window.HTMLTextAreaElement.prototype : window.HTMLInputElement.prototype, 'value')?.set;
        if (setter) setter.call(el, val);
        else el.value = val;
        ['input', 'change', 'blur'].forEach(e => el.dispatchEvent(new Event(e, { bubbles: true })));
    }

    function isVisible(el) {
        const r = el.getBoundingClientRect();
        return r.width > 0 && r.height > 0;
    }
})();
