import streamlit as st

def render_header():
    st.title("🤖 SAP Invoice Automator")
    st.markdown("Automate your invoice entry with precision.")

def render_sidebar():
    with st.sidebar:
        st.header("Settings")
        use_existing = st.checkbox("Attach to existing Chrome", value=True)
        return use_existing
