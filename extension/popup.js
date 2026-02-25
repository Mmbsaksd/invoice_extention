/* 
  Invoice Assistant - Popup Logic
*/

const API = "http://127.0.0.1:8000";
const $ = id => document.getElementById(id);

const UI = {
    // 1. RENDER: Show invoices as cards
    render(invoices) {
        const listContainer = $("list");
        if (!invoices.length) {
            listContainer.innerHTML = '<div class="empty">Ready for invoices.</div>';
            return;
        }

        listContainer.innerHTML = invoices.map((inv, i) => `
            <div class="card">
                <div class="card-top">
                    <span class="vendor">${inv.supplier || 'Unknown Vendor'}</span>
                    <span class="symbol" id="toggle-info-${i}" title="View Details">▾</span>
                </div>
                <div class="info">Amount: $${inv.amount || '0'}</div>
                
                <div class="details-box" id="details-${i}">
                    <b>Reference:</b> ${inv.reference || '-'}<br>
                    <b>Date:</b> ${inv.invoice_date || '-'}<br>
                    <b>Posting Date:</b> ${inv.posting_date || '-'}<br>
                    <b>Tax:</b> $${inv.tax_amount || '0.00'}
                </div>

                <div class="btns">
                    <button class="b-skip" id="skip-${i}">Skip</button>
                    <button class="b-fill" id="fill-${i}">Fill SAP</button>
                </div>
            </div>
        `).join('');

        // Attach Clicks
        invoices.forEach((_, i) => {
            $(`skip-${i}`).onclick = () => UI.skip(i);
            $(`fill-${i}`).onclick = () => UI.fill(i);

            // Expand/Collapse Details Logic
            const symbol = $(`toggle-info-${i}`);
            const details = $(`details-${i}`);
            symbol.onclick = () => {
                const isOpen = details.classList.contains('open');
                if (isOpen) {
                    details.classList.remove('open');
                    symbol.classList.remove('open');
                    symbol.innerText = '▾';
                } else {
                    details.classList.add('open');
                    symbol.classList.add('open');
                    symbol.innerText = '▴';
                }
            };
        });
    },

    async skip(index) {
        try {
            await fetch(`${API}/invoices/${index}`, { method: 'DELETE' });
            this.load();
        } catch (e) { console.error("API Error", e); }
    },

    async fill(index) {
        $("msg").innerText = "Connecting to page...";
        try {
            const res = await fetch(`${API}/invoices`);
            const invs = await res.json();
            const data = invs[index];
            chrome.runtime.sendMessage({ action: "FILL", data }, response => {
                if (response?.success) {
                    $("msg").innerText = "Filled!";
                    this.skip(index);
                } else {
                    $("msg").innerText = "Error: " + (response?.error || "Tab not active");
                }
            });
        } catch (e) { $("msg").innerText = "API Error"; }
    },

    async load() {
        try {
            const res = await fetch(`${API}/invoices`);
            const data = await res.json();
            this.render(data);
        } catch (e) { $("msg").innerText = "Connect API..."; }
    }
};

// --- THEME TOGGLE ---
$("theme-toggle").onclick = () => {
    const html = document.documentElement;
    const isDark = html.getAttribute('data-theme') === 'dark';
    const newTheme = isDark ? 'light' : 'dark';
    html.setAttribute('data-theme', newTheme);
    chrome.storage.local.set({ theme: newTheme });
};

// Load saved theme on startup
chrome.storage.local.get('theme', (res) => {
    if (res.theme) document.documentElement.setAttribute('data-theme', res.theme);
});


// --- BUTTON CLICKS ---
$("btn-upload").onclick = () => $("files").click();
$("files").onchange = async (e) => {
    if (!e.target.files.length) return;
    if (e.target.files.length > 10) {
        alert("Maximum 10 files allowed at once.");
        e.target.value = "";
        return;
    }
    $("msg").innerText = "Uploading...";
    const fd = new FormData();
    for (let f of e.target.files) fd.append('files', f);
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 60000); // 60s timeout

    try {
        const response = await fetch(`${API}/upload`, {
            method: 'POST',
            body: fd,
            signal: controller.signal
        });
        clearTimeout(timeout);

        if (!response.ok) {
            const err = await response.json();
            throw new Error(err.detail || "Server Error");
        }

        $("msg").innerText = "Done!";
        UI.load();
    } catch (e) {
        $("msg").innerText = e.name === 'AbortError' ? "Upload Timeout (60s)" : "Error: " + e.message;
    }
    e.target.value = "";
};

$("clear").onclick = async () => {
    if (confirm("Reset Session?")) {
        await fetch(`${API}/invoices`, { method: 'DELETE' });
        UI.load();
    }
};

UI.load();
