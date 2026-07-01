import streamlit as st
from src.utils.auth_helper import require_login

require_login()

if st.session_state.get("role") != "admin":
    st.error("Access Denied")
    st.stop()

st.title("🛡️ Admin Dashboard")

st.success("Administrator Access Granted")