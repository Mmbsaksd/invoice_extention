chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.action === "FILL_FORM") {
        console.log("Invoice Assistant: Received Fill Request", request.data);
        try {
            const data = request.data;
            clearAllSAPFields();

            // Priority 1: Specific SAP ID Selectors (High Confidence)
            const sapIdConfigs = [
                { sel: '[id*="Supplier"], [id*="Vendor"]', value: data.supplier },
                { sel: '[id*="InvoiceDate"], [id*="DocDate"], [id*="BLDAT"]', value: data.invoice_date },
                { sel: '[id*="PostingDate"], [id*="PstngDate"], [id*="BUDAT"]', value: data.posting_date },
                { sel: '[id*="Reference"], [id*="RefNo"], [id*="XBLNR"]', value: data.reference },
                { sel: '[id*="Amount"], [id*="GrossAmt"], [id*="WRBTR"]', value: data.amount },
                { sel: '[id*="TaxAmount"], [id*="TaxAmt"], [id*="WMWST"]', value: data.tax_amount }
            ];

            let filledCount = 0;
            let filledElements = new Set();

            sapIdConfigs.forEach(cfg => {
                if (cfg.value) {
                    const el = document.querySelector(cfg.sel);
                    if (el && isVisible(el)) {
                        console.log(`Invoice Assistant: ID Match found for: ${cfg.sel}`);
                        injectValue(el, cfg.value);
                        filledElements.add(el);
                        filledCount++;
                    }
                }
            });

            // Priority 2: Label-based Discovery (Fallback with Alignment)
            const fieldConfigs = [
                { id: "Supplier", labels: ["Supplier", "Vendor", "Supplier Name", "Creditor", "LIFNR"], value: data.supplier },
                { id: "Invoice date", labels: ["Invoice date", "Doc. Date", "Inv. Date", "Document Date", "BLDAT", "Inv.Date"], value: data.invoice_date },
                { id: "Posting Date", labels: ["Posting Date", "Pstng Date", "Journal Date", "BUDAT", "Pst.Date"], value: data.posting_date },
                { id: "Reference", labels: ["Reference", "Invoice Number", "Document No", "XBLNR", "Ref. No", "Inv.No"], value: data.reference },
                { id: "Amount", labels: ["Amount", "Gross Amount", "Total Amount", "WRBTR", "Gross Amt", "Total Amt"], value: data.amount },
                { id: "Tax Amount", labels: ["Tax Amount", "Tax", "VAT", "GST", "MwSt", "WMWST", "Tax Amt"], value: data.tax_amount }
            ];

            fieldConfigs.forEach(field => {
                if (field.value) {
                    for (const label of field.labels) {
                        const result = selectorLogic([label, "text"]);
                        if (result.status === "OK" && !filledElements.has(result.element)) {
                            console.log(`Invoice Assistant: SUCCESS! Label found: '${label}'. Injecting: ${field.value}`);
                            injectValue(result.element, field.value);
                            filledElements.add(result.element);
                            filledCount++;
                            break;
                        }
                    }
                }
            });

            console.log(`Invoice Assistant: Fill cycle complete. Fields filled: ${filledCount}/${fieldConfigs.filter(f => f.value).length}`);
            sendResponse({ success: true, filled: filledCount });
        } catch (e) {
            console.error("Fill Error:", e);
            sendResponse({ success: false, error: e.message });
        }
    }
    return true;
});

function injectValue(el, val) {
    if (!el || val === undefined) return;
    try {
        // Client-side sanitization for Numeric fields (Amount/Tax)
        const id = (el.id || el.name || '').toLowerCase();
        const cleanedVal = (id.includes('amount') || id.includes('amt') || id.includes('wrbtr'))
            ? val.toString().replace(/[^\d.]/g, '')
            : val;

        console.log(`Invoice Assistant: Injecting into '${el.id || el.name}': [${cleanedVal}] (original: ${val})`);

        el.focus();
        const isInput = el instanceof HTMLInputElement || el instanceof HTMLTextAreaElement;
        if (isInput) {
            // Clean Sweep: Atomic value update to trigger React/UI frameworks
            const proto = el instanceof HTMLTextAreaElement ? window.HTMLTextAreaElement.prototype : window.HTMLInputElement.prototype;
            const setter = Object.getOwnPropertyDescriptor(proto, 'value').set;
            setter.call(el, ''); // Force clear
            el.dispatchEvent(new Event('input', { bubbles: true }));
            setter.call(el, cleanedVal);
        } else {
            el.innerText = cleanedVal;
        }
        ['input', 'change', 'blur'].forEach(ev => el.dispatchEvent(new Event(ev, { bubbles: true })));
    } catch (e) {
        console.warn("Direct injection fallback", e);
        el.value = val;
        el.dispatchEvent(new Event('input', { bubbles: true }));
    }
}

function isVisible(el) {
    const rect = el.getBoundingClientRect();
    return rect.width > 0 && rect.height > 0;
}

function clearAllSAPFields() {
    console.log("Invoice Assistant: Running Clean Slate...");
    const commonSels = [
        '[id*="Supplier"], [id*="Vendor"]',
        '[id*="InvoiceDate"], [id*="DocDate"], [id*="BLDAT"]',
        '[id*="PostingDate"], [id*="PstngDate"], [id*="BUDAT"]',
        '[id*="Reference"], [id*="RefNo"], [id*="XBLNR"]',
        '[id*="Amount"], [id*="GrossAmt"], [id*="WRBTR"]',
        '[id*="TaxAmount"], [id*="TaxAmt"], [id*="WMWST"]'
    ];
    commonSels.forEach(sel => {
        try {
            document.querySelectorAll(sel).forEach(el => {
                if (el && (el.value || el.innerText)) {
                    el.value = '';
                    el.innerText = '';
                    ['input', 'change', 'blur'].forEach(ev => el.dispatchEvent(new Event(ev, { bubbles: true })));
                }
            });
        } catch (e) { }
    });
}
