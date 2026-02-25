const API = "http://127.0.0.1:8000";
const $ = id => document.getElementById(id);

const UI = {
    render(invoices) {
        if (!invoices.length) return $("list").innerHTML = '<div class="empty">Ready for invoices.</div>';
        $("list").innerHTML = invoices.map((inv, i) => `
            <div class="card">
                <span class="vendor">${inv.supplier || 'Unknown'}</span>
                <div class="info">Ref: ${inv.reference || '-'}<br>Amount: $${inv.amount || '0'}</div>
                <div class="btns">
                    <button class="b-skip" onclick="UI.skip(${i})">Skip</button>
                    <button class="b-fill" onclick="UI.fill(${i})">Fill SAP</button>
                </div>
            </div>
        `).join('');
    },
    async skip(i) {
        await fetch(`${API}/invoices/${i}`, { method: 'DELETE' });
        this.load();
    },
    async fill(i) {
        const invs = await (await fetch(`${API}/invoices`)).json();
        const data = invs[i];
        $("msg").innerText = "Filling...";
        chrome.runtime.sendMessage({ action: "FILL", data }, r => {
            if (r?.success) {
                $("msg").innerText = "Filled!";
                this.skip(i);
            } else $("msg").innerText = "Error: " + (r?.error || "Tab not ready");
        });
    },
    async load() {
        try {
            const data = await (await fetch(`${API}/invoices`)).json();
            this.render(data);
        } catch (e) { $("msg").innerText = "Connect API..."; }
    }
};

$("files").onchange = async (e) => {
    if (!e.target.files.length) return;
    $("msg").innerText = "Uploading...";
    const fd = new FormData();
    for (let f of e.target.files) fd.append('files', f);
    try {
        await fetch(`${API}/upload`, { method: 'POST', body: fd });
        $("msg").innerText = "Complete!";
        UI.load();
    } catch (e) { $("msg").innerText = "Error uploading"; }
    e.target.value = "";
};

$("clear").onclick = async () => {
    if (confirm("Reset?")) {
        await fetch(`${API}/invoices`, { method: 'DELETE' });
        UI.load();
    }
};

UI.load();
window.UI = UI; // Export to HTML
