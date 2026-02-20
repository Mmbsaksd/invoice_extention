import os
import json
import asyncio
from tempfile import NamedTemporaryFile
import streamlit as st
import nest_asyncio
from dotenv import load_dotenv

# --- CONFIGURATION ---
load_dotenv(override=True)
nest_asyncio.apply()

# Proactor policy for Windows/Playwright
if os.name == 'nt':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

from main import process_invoice
from sap_automation import run_single_fill

st.set_page_config(page_title="SAP Automator", page_icon="🤖", layout="wide")

# --- UI HELPERS ---
def get_status():
    """Checks for active LLM keys."""
    return any(os.getenv(k) for k in ["AZURE_OPENAI_API_KEY", "OPENAI_API_KEY", "GOOGLE_API_KEY"])

def process_file(file):
    """Temporary file handling and extraction."""
    with NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(file.getvalue())
        path = tmp.name
    try:
        return process_invoice(path)
    finally:
        if os.path.exists(path): os.remove(path)

# --- UI COMPONENT: Sidebar ---
def render_sidebar():
    with st.sidebar:
        st.header("Connection")
        if get_status():
            st.success("✅ LLM Connected")
        else:
            st.error("❌ No API Keys")
        
        st.divider()
        st.header("⚙️ Settings")
        use_existing = st.checkbox("Existing Browser Mode", value=True)
        
        if use_existing:
            st.caption("🚀 **How to enable:**")
            st.code('cmd /c "start chrome --remote-debugging-port=9222 --user-data-dir=C:\\temp\\chrome_dev"', language='bash')
        
    return use_existing

# --- UI COMPONENT: Master Table ---
def render_master_table(use_existing):
    if not st.session_state.get('pending_invoices'):
        st.info("👋 No pending invoices. Upload files to begin.")
        return

    st.subheader(f"📋 Master Extraction Table ({len(st.session_state.pending_invoices)})")
    
    url = st.text_input("SAP URL", placeholder="https://...", value=st.session_state.get('sap_url', ""))
    st.session_state.sap_url = url

    # Table Header
    cols = st.columns([2, 1.5, 1.5, 1.5, 1, 1, 1.5])
    header_style = "color:#6b7785; font-size:0.8rem; font-weight:700; text-transform:uppercase"
    labels = ["Supplier", "Inv Date", "Reference", "Post Date", "Amount", "Tax", "Action"]
    for col, label in zip(cols, labels):
        col.markdown(f'<p style="{header_style}">{label}</p>', unsafe_allow_html=True)
    
    st.divider()

    # Table Rows
    to_remove = None
    for i, inv in enumerate(st.session_state.pending_invoices):
        err = inv.get("validation_error")
        bg_color = "#fff0f0" if err else "transparent"
        
        with st.container():
            st.markdown(f'<div style="background-color:{bg_color}; padding:5px; border-radius:4px">', unsafe_allow_html=True)
            row_cols = st.columns([2, 1.5, 1.5, 1.5, 1, 1, 1.5])
            
            row_cols[0].write(inv.get("supplier", "N/A"))
            row_cols[1].write(inv.get("invoice_date", "N/A"))
            row_cols[2].write(inv.get("reference", "N/A"))
            row_cols[3].write(inv.get("posting_date", "N/A"))
            row_cols[4].write(inv.get("amount", "0.00"))
            row_cols[5].write(inv.get("tax_amount", "0.00"))
            
            # Action Button
            if err:
                row_cols[6].error("⚠️ Check Data")
                st.caption(f":red[{err}]")
            else:
                if row_cols[6].button(f"Fill SAP", key=f"fill_{i}"):
                    if not url:
                        st.warning("SAP URL required")
                    else:
                        with st.spinner(f"Filling {inv.get('reference')}..."):
                            res = asyncio.run(run_single_fill(inv, url, use_existing))
                            if res["status"] == "success":
                                st.toast(res["message"], icon="✅")
                                to_remove = i
                            else:
                                st.error(res["message"])
            st.markdown('</div>', unsafe_allow_html=True)

    if to_remove is not None:
        st.session_state.pending_invoices.pop(to_remove)
        st.rerun()

    if st.button("🗑️ Clear All Rows"):
        st.session_state.pending_invoices = []
        st.rerun()

def main():
    st.title("🤖 SAP Production-Grade Agent")
    st.markdown("_High-Accuracy Assisted Filling_")
    
    if 'pending_invoices' not in st.session_state:
        st.session_state.pending_invoices = []
    if 'processed_file_hashes' not in st.session_state:
        st.session_state.processed_file_hashes = set()

    use_existing = render_sidebar()
    files = st.file_uploader("Upload Invoice(s)", type=['pdf'], accept_multiple_files=True)
    
    if files:
        new_invoices = []
        # Filter only truly NEW files based on content hash/name to enforce LLM-Once
        files_to_process = [f for f in files if f.name not in st.session_state.processed_file_hashes]
        
        if files_to_process:
            with st.spinner("Analyzing New Uploads..."):
                for file in files_to_process:
                    try:
                        results = process_file(file)
                        if results: 
                            new_invoices.extend(results)
                        st.session_state.processed_file_hashes.add(file.name)
                    except Exception as e:
                        st.error(f"Error processing {file.name}: {e}")
        
        if new_invoices:
            current_refs = {f"{inv.get('supplier')}_{inv.get('reference')}".lower() for inv in st.session_state.pending_invoices}
            for inv in new_invoices:
                ref_key = f"{inv.get('supplier')}_{inv.get('reference')}".lower()
                if ref_key not in current_refs:
                    st.session_state.pending_invoices.append(inv)
                    current_refs.add(ref_key)

    render_master_table(use_existing)

if __name__ == "__main__":
    main()
