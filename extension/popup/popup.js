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
    async fetchInvoices() {
        try {
            const res = await fetch(`${API_BASE}/invoices`);
            const data = await res.json();
            return Array.isArray(data) ? data : [];
        } catch { return []; }
    },
    async uploadFiles(files) {
        const formData = new FormData();
        for (let i = 0; i < files.length; i++) {
            formData.append('files', files[i]);
        }
        const res = await fetch(`${API_BASE}/upload`, {
            method: 'POST',
            body: formData
        });
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
                <div class="footer-tools">
                    <button class="btn-skip" data-index="${index}">Skip</button>
                    <button class="btn-fill" data-index="${index}">Fill SAP</button>
                </div>
            `;

            const fillBtn = card.querySelector('.btn-fill');
            const skipBtn = card.querySelector('.btn-skip');

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
        this.updateStatus(`Filling ${inv.reference || 'invoice'}...`, 'loading');
        chrome.runtime.sendMessage({ action: "FILL_FORM", data: inv }, (response) => {
            if (response && response.success) {
                this.updateStatus("Fill complete!", 'default');
                this.removeRow(card, inv);
            } else {
                this.updateStatus("Error: " + (response ? response.error : "Failed"), 'error');
            }
        });
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
            UIController.updateStatus(`Uploading ${fileInput.files.length} file(s)...`, 'loading');
            const results = await ApiService.uploadFiles(fileInput.files);
            UIController.updateStatus("Processing complete!", 'default');

            // Auto refresh
            State.invoices = await ApiService.fetchInvoices();
            await StorageManager.save();
            UIController.renderList();
        } catch (e) {
            UIController.updateStatus("Upload failed.", 'error');
            console.error(e);
        } finally {
            fileInput.value = ''; // Reset
        }
    };

    refreshBtn.onclick = async () => {
        try {
            UIController.updateStatus("Syncing...", 'loading');
            State.invoices = await ApiService.fetchInvoices();
            await StorageManager.save();
            UIController.renderList();
            UIController.updateStatus("Refreshed.", 'default');
        } catch (e) {
            UIController.updateStatus("Error: API Offline", 'error');
            console.error(e);
        }
    };
});
