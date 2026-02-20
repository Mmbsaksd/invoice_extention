import streamlit as st
from shared.config import init_config
from storage.session_store import session_store
from web_app.ui.components import render_sidebar, render_header
from web_app.controllers.main_controller import handle_file_upload, handle_fill_sap
import asyncio

# Initialization
init_config()

st.set_page_config(page_title="Invoice Assistant", page_icon="🤖", layout="wide")

# Premium UI Styling (Dark Mode)
st.markdown("""
<style>
    .stApp {
        background: #171717;
        color: #ececf1;
    }
    .main-card {
        background: #212121;
        border: 1px solid #444654;
        border-radius: 12px;
        padding: 24px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.3);
        margin-bottom: 20px;
    }
    .invoice-row {
        background: #2f2f2f;
        border-radius: 10px;
        padding: 15px;
        margin-bottom: 12px;
        border-left: 4px solid #10a37f;
        transition: 0.2s;
    }
    .invoice-row:hover {
        background: #353641;
        transform: scale(1.01);
    }
    .stButton>button {
        border-radius: 6px;
        font-weight: 500;
        background-color: #343541 !important;
        color: white !important;
        border: 1px solid #565869 !important;
    }
    .stButton>button:hover {
        background-color: #40414f !important;
        border-color: #acacbe !important;
    }
    .btn-fill {
        background: #10a37f !important;
        border: none !important;
    }
    .stHeader { color: #10a37f; }
    h1, h2, h3, p, span, label {
        color: #ececf1 !important;
    }
    .stCaption {
        color: #9ea1b1 !important;
    }
    /* Sidebar styling */
    [data-testid="stSidebar"] {
        background-color: #171717 !important;
        border-right: 1px solid #444654 !important;
    }
    [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 {
        color: #10a37f !important;
    }
</style>
""", unsafe_allow_html=True)

def main():
    render_header()
    use_existing = render_sidebar()
    
    with st.container():
        st.markdown('<div class="main-card">', unsafe_allow_html=True)
        files = st.file_uploader("📂 **Drop Invoices Here** (Multi-PDF Support)", type=['pdf'], accept_multiple_files=True)
        st.markdown('</div>', unsafe_allow_html=True)

    if files:
        processed_any = False
        for file in files:
            if file.name not in session_store.processed_file_hashes:
                with st.spinner(f"🚀 Analyzing {file.name}..."):
                    handle_file_upload(file)
                    processed_any = True
        if processed_any:
            st.rerun()

    invoices = session_store.pending_invoices
    if invoices:
        st.subheader(f"📋 Pending Invoices ({len(invoices)})")
        
        # Global URL Config
        url = st.text_input("🔗 SAP Automation Target URL", value=session_store.sap_url)
        session_store.sap_url = url

        for i, inv in enumerate(invoices):
            with st.container():
                st.markdown('<div class="invoice-row">', unsafe_allow_html=True)
                cols = st.columns([3, 1, 1, 1])
                
                # Info
                cols[0].markdown(f"**{inv.get('supplier', 'Unknown')}**")
                cols[0].caption(f"Ref: {inv.get('reference', '---')} | Date: {inv.get('invoice_date', '---')}")
                
                # Amount
                cols[1].markdown(f"**${inv.get('amount', '0.00')}**")
                cols[1].caption(f"Tax: ${inv.get('tax_amount', '0.00')}")

                # Actions
                if cols[2].button("🗑️ Skip", key=f"s_{i}"):
                    session_store.remove_invoice(i)
                    st.rerun()

                if cols[3].button("⚡ Fill SAP", key=f"f_{i}", type="primary"):
                    if not url:
                        st.error("Please enter a SAP URL first!")
                    else:
                        with st.spinner("🤖 Automating..."):
                            loop = asyncio.new_event_loop()
                            asyncio.set_event_loop(loop)
                            res = loop.run_until_complete(handle_fill_sap(inv, url, use_existing))
                            if res["status"] == "success":
                                st.toast("✅ Fill Success!")
                                session_store.remove_invoice(i)
                                st.rerun()
                            else:
                                st.error(res["message"])
                st.markdown('</div>', unsafe_allow_html=True)

    if st.button("🧼 Clear All Data"):
        session_store.clear()
        st.rerun()

if __name__ == "__main__":
    main()
