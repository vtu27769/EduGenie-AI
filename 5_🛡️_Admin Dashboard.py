import streamlit as st
import pandas as pd

from src.utils.auth_helper import require_login

from src.database.db_manager import (
    get_total_users,
    get_total_documents,
    get_total_notes,
    get_total_quizzes,
    get_all_users
)

require_login()


st.title("🛡️ Admin Dashboard")

total_users = get_total_users()
total_docs = get_total_documents()
total_notes = get_total_notes()
total_quizzes = get_total_quizzes()

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Users", total_users)

with col2:
    st.metric("PDFs", total_docs)

with col3:
    st.metric("Notes", total_notes)

with col4:
    st.metric("Quizzes", total_quizzes)

st.divider()

st.subheader("👥 User Management")

users = get_all_users()

if users:
    df = pd.DataFrame(users)
    st.dataframe(df, use_container_width=True)
else:
    st.info("No users found.")