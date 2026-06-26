import os
import streamlit as st
from pathlib import Path
from src.config import CHROMA_DB_DIR, SQLITE_DB_PATH, BASE_DIR
from src.database.db_manager import get_user_documents
from langchain_google_genai import ChatGoogleGenerativeAI
from src.utils.auth_helper import require_login, logout_user

# 1. Protect page - Redirect to login if unauthorized
require_login()

user_id = st.session_state.user_id
username = st.session_state.username

# Configure page
st.set_page_config(
    page_title="Settings - EduGenie AI",
    page_icon="⚙️",
    layout="wide"
)

# Load external custom styling
def load_css(css_file_path: Path):
    if css_file_path.exists():
        with open(css_file_path, "r", encoding="utf-8") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

css_path = Path(__file__).resolve().parent.parent / "src" / "ui" / "styles.css"
load_css(css_path)

st.markdown("<h1 class='main-title'>⚙️ Settings & Status</h1>", unsafe_allow_html=True)
st.markdown("<p class='subtitle'>Manage application configurations, API credentials, and project database parameters.</p>", unsafe_allow_html=True)

# 2. Retrieve user documents
user_docs = get_user_documents(user_id)
total_docs = len(user_docs)

# Sidebar active document control
with st.sidebar:
    st.image("https://img.icons8.com/clouds/200/genie.png", width=100)
    st.header("EduGenie AI")
    st.caption(f"👤 User: {username}")
    st.markdown("---")
    
    st.subheader("📁 Study Library")
    if total_docs > 0:
        doc_options = [doc["file_name"] for doc in user_docs]
        
        # Determine default index
        default_idx = 0
        active_doc = st.session_state.get("active_document_name")
        if active_doc in doc_options:
            default_idx = doc_options.index(active_doc)
            
        selected_doc = st.selectbox("Select active document:", doc_options, index=default_idx, key="settings_select_doc")
        
        if selected_doc != active_doc:
            st.session_state.active_document_name = selected_doc
            # Set the active path in RAGPipeline
            matching_doc_path = next(doc["file_path"] for doc in user_docs if doc["file_name"] == selected_doc)
            if "pipeline" in st.session_state:
                st.session_state.pipeline.current_pdf_path = Path(matching_doc_path)
            st.rerun()
            
        st.success(f"📄 Active: {selected_doc}")
    else:
        st.info("No study materials found. Please upload documents in the dashboard first.")
        
    st.markdown("---")
    if st.button("📊 Go to Dashboard", use_container_width=True):
        st.switch_page("app.py")
    if st.button("📖 Study Assistant", use_container_width=True):
        st.switch_page("pages/1_📖_Study_Assistant.py")
    if st.button("🚪 Logout", use_container_width=True):
        logout_user()

# Main settings layout
col_left, col_right = st.columns([2, 1])

# Fetch API Key
current_key = os.getenv("GOOGLE_API_KEY")
if not current_key or current_key == "YOUR_GEMINI_API_KEY":
    current_key = ""
has_key = bool(current_key.strip())

with col_left:
    st.write("### 🔑 Google Gemini API Credentials")
    
    # Key input (obfuscated)
    new_key = st.text_input(
        "Google Gemini API Key:",
        value=current_key,
        type="password",
        placeholder="Enter your AI Studio API key...",
        help="Obtain an API key from Google AI Studio (https://aistudio.google.com/)"
    )
    
    if st.button("Save Credentials", key="btn_save_settings", use_container_width=True):
        try:
            # Update running environment variable
            os.environ["GOOGLE_API_KEY"] = new_key
            
            # Write to .env file in root directory for persistence
            env_file_path = BASE_DIR / ".env"
            with open(env_file_path, "w", encoding="utf-8") as f:
                f.write(f"GOOGLE_API_KEY={new_key}\n")
                
            st.success("✅ Credentials saved and persisted successfully! Environment refreshed.")
            st.rerun()
        except Exception as e:
            st.error(f"Failed to persist credentials: {e}")
            
    st.write("---")
    st.write("### 🎨 UI & Themes")
    
    # Theme toggle placeholder
    theme_option = st.toggle(
        "Enable Dark Accent Mode",
        value=True,
        help="Placeholder: toggle between custom dark accent styling and default light styles."
    )
    
    if theme_option:
        st.caption("✨ Dark accent styling is currently applied via styles.css.")
    else:
        st.caption("💡 Streamlit default styling interface is active.")

with col_right:
    st.write("### 🔍 Application Status")
    
    # 1. API Status
    st.write("**Gemini API Key Status:**")
    if has_key:
        st.markdown("<span style='color:#6BCB77; font-weight:bold;'>Configured Key Found ✅</span>", unsafe_allow_html=True)
        
        # Test connection button
        if st.button("Test Connection", key="btn_test_api", use_container_width=True):
            with st.spinner("Testing communication with Gemini API..."):
                try:
                    # Make a simple test request
                    test_llm = ChatGoogleGenerativeAI(
                        model="gemini-2.5-flash",
                        google_api_key=current_key,
                        temperature=0.2
                    )
                    # Invoke a simple prompt to test the model
                    test_llm.invoke("Say connection successful in 3 words")
                    st.success("🎉 Success: Connected to Google Gemini API!")
                except Exception as e:
                    st.error(f"Failed connection: {e}")
    else:
        st.markdown("<span style='color:#FF6B6B; font-weight:bold;'>Missing Key ❌</span>", unsafe_allow_html=True)
        st.info("API features will remain locked until a valid key is added.")
        
    st.write("---")
    
    # 2. Database Paths
    st.write("**Vector Storage Path (ChromaDB):**")
    st.code(str(CHROMA_DB_DIR))
    
    st.write("**Relational Storage Path (SQLite):**")
    st.code(str(SQLITE_DB_PATH))
