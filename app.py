import streamlit as st
import json
import os
from tempfile import NamedTemporaryFile
from main import process_invoice

st.set_page_config(page_title="Invoice Extractor", page_icon="📄")

st.title("📄 Invoice Extractor")

# Minimal API Key Check
azure_key = os.getenv("AZURE_OPENAI_API_KEY")
openai_key = os.getenv("OPENAI_API_KEY")
google_key = os.getenv("GOOGLE_API_KEY")

if not any([azure_key, openai_key, google_key]):
    st.error("No API Keys found. Please check your .env file.")
else:
    st.sidebar.success("✅ Connected")

uploaded_file = st.file_uploader("Upload Invoice PDF", type=['pdf'])

if uploaded_file:
    with NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(uploaded_file.getvalue())
        path = tmp.name

    with st.spinner("Extracting..."):
        try:
            data = process_invoice(path)
            st.success("Extraction Complete!")
            
            # Show summary
            st.write(f"**Invoice Number:** {data.get('invoice_number')}")
            st.write(f"**Total:** ₹{data.get('grand_total')}")
            
            # Show Table
            if data.get('products'):
                st.table(data['products'])
            
            # Show Full JSON
            with st.expander("View Full JSON"):
                st.json(data)
                st.download_button("Download JSON", json.dumps(data, indent=2), "invoice.json")
                
        except Exception as e:
            st.error(f"Error: {e}")
        finally:
            if os.path.exists(path):
                os.remove(path)
