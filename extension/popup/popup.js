const API_BASE = "http://127.0.0.1:8000";

let State = {
    invoices: [],
    processedCount: 0
};

const StorageManager = {
    async save() {
        await chrome.storage.local.set({ state: State });
    },
    async load() {
        const data = await chrome.storage.local.get('state');
        if (data.state) State = data.state;
    }
};

const ApiService = {
    async fetchWithTimeout(url, options = {}, timeout = 30000) {
        const controller = new AbortController();
        const id = setTimeout(() => controller.abort(), timeout);
        try {
            const response = await fetch(url, { ...options, signal: controller.signal });
            clearTimeout(id);
            return response;
        } catch (e) {
            clearTimeout(id);
            throw e;
        }
    },
    async fetchInvoices() {
        try {
            const res = await this.fetchWithTimeout(`${API_BASE}/invoices`, {}, 5000);
            const data = await res.json();
            return Array.isArray(data) ? data : [];
        } catch (e) {
            console.error("Fetch Invoices Failed:", e);
            return [];
        }
    },
    async uploadFiles(files) {
        const formData = new FormData();
        for (let i = 0; i < files.length; i++) {
            formData.append('files', files[i]);
        }
        const res = await this.fetchWithTimeout(`${API_BASE}/upload`, {
            method: 'POST',
            body: formData
        }, 120000); // 2 minute timeout for uploads
        if (!res.ok) {
            const err = await res.json();
            throw new Error(err.detail || "Server Error");
        }
        return await res.json();
    },
    async clearAll() {
        await fetch(`${API_BASE}/invoices`, { method: 'DELETE' });
    }
};

const UIController = {
    list: document.getElementById('invoice-list'),
    status: document.getElementById('status-text'),
    statusBar: document.getElementById('status-bar'),

    renderList() {
        if (!State.invoices || State.invoices.length === 0) {
            this.list.innerHTML = `<div class="empty-state">No invoices found.<br><small>Ready to process your PDFs.</small></div>`;
            return;
        }

        this.list.innerHTML = '';
        State.invoices.forEach((inv, index) => {
            const card = document.createElement('div');
            card.className = 'card';
            card.innerHTML = `
                <span class="status-badge">Ready</span>
                <span class="vendor">${inv.supplier || 'Unknown Vendor'}</span>
                <div class="details">
                    Ref: ${inv.reference || '---'}<br>
                    Amount: $${inv.amount || '0.00'}
                </div>
                
                <div class="details-expandable" id="details-${index}">
                    <div class="detail-row"><span class="detail-label">Invoice Date:</span> <span class="detail-value">${inv.invoice_date || '---'}</span></div>
                    <div class="detail-row"><span class="detail-label">Posting Date:</span> <span class="detail-value">${inv.posting_date || '---'}</span></div>
                    <div class="detail-row"><span class="detail-label">Tax Amount:</span> <span class="detail-value">$${inv.tax_amount || '0.00'}</span></div>
                    ${inv.validation_error ? `<div class="detail-row" style="color:#ea4335"><span class="detail-label">Note:</span> <span class="detail-value">${inv.validation_error}</span></div>` : ''}
                </div>

                <div class="footer-tools">
                    <button class="toggle-btn" id="toggle-${index}">Details</button>
                    <div class="btn-group">
                        <button class="btn-skip" data-index="${index}">Skip</button>
                        <button class="btn-fill" data-index="${index}">Fill SAP</button>
                    </div>
                </div>
            `;

            const toggleBtn = card.querySelector(`#toggle-${index}`);
            const expandable = card.querySelector(`#details-${index}`);
            const fillBtn = card.querySelector('.btn-fill');
            const skipBtn = card.querySelector('.btn-skip');

            toggleBtn.onclick = () => {
                expandable.classList.toggle('active');
                toggleBtn.innerText = expandable.classList.contains('active') ? 'Hide' : 'Details';
            };

            fillBtn.onclick = () => this.handleFill(inv, card);
            skipBtn.onclick = () => this.removeRow(card, inv);

            this.list.appendChild(card);
        });
    },

    updateStatus(msg, type = 'default') {
        this.status.innerText = msg;
        const dot = this.statusBar.querySelector('.dot');
        if (type === 'error') dot.style.background = '#ea4335';
        else if (type === 'loading') dot.style.background = '#fbbc05';
        else dot.style.background = '#34a853';
    },

    async handleFill(inv, card) {
        const fillBtn = card.querySelector('.btn-fill');
        const originalText = fillBtn.innerText;

        try {
            this.updateStatus(`Filling ${inv.reference || 'invoice'}...`, 'loading');
            fillBtn.classList.add('loading');
            fillBtn.innerText = 'Wait...';
            fillBtn.disabled = true;

            chrome.runtime.sendMessage({ action: "FILL_FORM", data: inv }, (response) => {
                fillBtn.classList.remove('loading');
                fillBtn.innerText = originalText;
                fillBtn.disabled = false;

                const err = chrome.runtime.lastError;
                if (err) {
                    this.updateStatus("Extension Error: Please REFRESH the page.", 'error');
                    console.error("Popup Message Error:", err);
                    return;
                }

                if (response && response.success) {
                    const filledMsg = response.filled !== undefined ? ` (${response.filled} fields)` : '';
                    this.updateStatus(`Done!${filledMsg}`, 'default');
                    this.removeRow(card, inv);
                } else {
                    const errorMsg = response ? response.error : "No response from page";
                    this.updateStatus("Error: " + errorMsg, 'error');
                }
            });
        } catch (e) {
            console.error("HandleFill Exception:", e);
            fillBtn.classList.remove('loading');
            fillBtn.innerText = originalText;
            fillBtn.disabled = false;
        }
    },

    removeRow(card, inv) {
        card.classList.add('fade-out');
        setTimeout(() => {
            card.remove();
            State.invoices = State.invoices.filter(i => i !== inv);
            StorageManager.save();
            if (State.invoices.length === 0) this.renderList();
        }, 300);
    }
};

// Start
document.addEventListener('DOMContentLoaded', async () => {
    await StorageManager.load();
    UIController.renderList();

    const fileInput = document.getElementById('file-input');
    const uploadBtn = document.getElementById('btn-upload');
    const refreshBtn = document.getElementById('btn-refresh');

    uploadBtn.onclick = () => fileInput.click();

    fileInput.onchange = async () => {
        if (fileInput.files.length === 0) return;

        try {
            const count = fileInput.files.length;
            const statusMsg = count > 1 ? `Processing batch of ${count} files...` : `Uploading ${count} file(s)...`;
            UIController.updateStatus(statusMsg, 'loading');
            const results = await ApiService.uploadFiles(fileInput.files);

            if (!results || results.length === 0) {
                UIController.updateStatus("No invoices found. Ensure OCR dependencies are installed.", 'error');
            } else {
                UIController.updateStatus("Processing complete!", 'default');
            }

            // Auto refresh
            State.invoices = await ApiService.fetchInvoices();
            await StorageManager.save();
            UIController.renderList();
        } catch (e) {
            let msg = "Upload failed.";
            if (e.name === 'AbortError') msg = "Timeout: Server took too long.";
            else if (e.message) msg = `Error: ${e.message.split('\n')[0]}`;
            UIController.updateStatus(msg, 'error');
            console.error(e);
        } finally {
            fileInput.value = ''; // Reset
        }
    };

    refreshBtn.onclick = async () => {
        if (!confirm("Clear all processed invoices and reset?")) return;
        try {
            UIController.updateStatus("Clearing all data...", 'loading');
            await ApiService.clearAll();
            State.invoices = [];
            await StorageManager.save();
            UIController.renderList();
            UIController.updateStatus("System Reset.", 'default');
        } catch (e) {
            UIController.updateStatus("Reset failed.", 'error');
            console.error(e);
        }
    };
});
