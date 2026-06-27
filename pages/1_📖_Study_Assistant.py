import streamlit as st
import os
from pathlib import Path
from src.config import UPLOAD_DIR, validate_config
from src.database.db_manager import (
    get_user_documents, add_uploaded_document, save_chat_message, 
    get_chat_history, clear_chat_history, save_note
)
from src.utils.auth_helper import require_login, logout_user

# 1. Protect page - Redirect to login if unauthorized
require_login()

user_id = st.session_state.user_id
username = st.session_state.username

# Configure page
st.set_page_config(
    page_title="Study Assistant - EduGenie AI",
    page_icon="📖",
    layout="wide"
)

# Load external custom styling
def load_css(css_file_path: Path):
    if css_file_path.exists():
        with open(css_file_path, "r", encoding="utf-8") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

css_path = Path(__file__).resolve().parent.parent / "src" / "ui" / "styles.css"
load_css(css_path)

st.markdown("<h1 class='main-title'>📖 Study Assistant</h1>", unsafe_allow_html=True)
st.markdown("<p class='subtitle'>Engage in conversational question-answering or generate detailed study notes based on your documents.</p>", unsafe_allow_html=True)

# 2. Validate configuration (e.g., API key presence)
api_key_valid = True
try:
    validate_config()
except ValueError as e:
    api_key_valid = False
    st.warning("⚠️ Configuration Alert: Google Gemini API Key is missing.")
    st.info("Please navigate to the ⚙️ Settings page or sidebar to configure your credentials.")

# 3. Retrieve user documents
user_docs = get_user_documents(user_id)
total_docs = len(user_docs)

# Sidebar info & Active Document Control
with st.sidebar:
    st.image("https://img.icons8.com/clouds/200/genie.png", width=100)
    st.header("EduGenie AI")
    st.caption(f" User: {username}")
    st.markdown("---")
    
    st.subheader(" Study Library")
    if total_docs > 0:
        doc_options = [doc["file_name"] for doc in user_docs]
        
        # Determine default index
        default_idx = 0
        active_doc = st.session_state.get("active_document_name")
        if active_doc in doc_options:
            default_idx = doc_options.index(active_doc)
            
        selected_doc = st.selectbox("Select active document:", doc_options, index=default_idx, key="assistant_select_doc")
        
        if selected_doc != active_doc:
            st.session_state.active_document_name = selected_doc
            # Set the active path in RAGPipeline
            matching_doc_path = next(doc["file_path"] for doc in user_docs if doc["file_name"] == selected_doc)
            if "pipeline" in st.session_state:
                st.session_state.pipeline.current_pdf_path = Path(matching_doc_path)
            st.rerun()
            
        st.success(f"📄 Active: {selected_doc}")
    else:
        st.info("Your library is empty. Please upload documents from the dashboard or below.")
        
    st.markdown("---")
    if st.button("📊 Go to Dashboard", use_container_width=True):
        st.switch_page("app.py")
    if st.button("⚙️ Settings", use_container_width=True):
        st.switch_page("pages/3_⚙️_Settings.py")
    if st.button("🚪 Logout", use_container_width=True):
        logout_user()

# Main page logic
if api_key_valid:
    pipeline = st.session_state.get("pipeline")
    
    # Render uploader if library is empty or as an option
    if total_docs == 0:
        st.info("👋 Upload your first study document to start learning.")
        uploaded_file = st.file_uploader(
            "Upload PDF textbook, class notes, or study materials:",
            type=["pdf"],
            help="Upload PDF files to start learning."
        )
        if uploaded_file is not None:
            with st.spinner(f"Uploading and indexing '{uploaded_file.name}'..."):
                try:
                    user_upload_dir = UPLOAD_DIR / f"user_{user_id}"
                    user_upload_dir.mkdir(parents=True, exist_ok=True)
                    
                    saved_path = user_upload_dir / uploaded_file.name
                    with open(saved_path, "wb") as f:
                        f.write(uploaded_file.getbuffer())
                    
                    pipeline.index_pdf(str(saved_path), user_id)
                    add_uploaded_document(user_id, uploaded_file.name, str(saved_path), uploaded_file.size)
                    
                    st.session_state.active_document_name = uploaded_file.name
                    st.success("✅ Success! File uploaded and indexed.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error processing file: {e}")
                    
    # Interactive features
    active_doc_name = st.session_state.get("active_document_name")
    if active_doc_name:
        # Load active document path if not set in pipeline
        if pipeline and not pipeline.current_pdf_path:
            matching_docs = [d for d in user_docs if d["file_name"] == active_doc_name]
            if matching_docs:
                pipeline.current_pdf_path = Path(matching_docs[0]["file_path"])
                
        st.markdown(f"#### Active Document: **{active_doc_name}**")
        
        tab_qa, tab_notes = st.tabs(["💬 Chat with PDF", "📝 Study Notes Compiler"])
        
        with tab_qa:
            st.write("### Ask Questions About Your Material")
            
            # Display Chat Messages
           # Display Chat Messages (Custom UI without avatars)

chat_history = get_chat_history(user_id)

st.markdown("""
<style>
.user-message {
    background: #1e293b;
    color: white;
    padding: 14px;
    border-radius: 12px;
    margin-bottom: 10px;
    border-left: 4px solid #38bdf8;
}

.assistant-message {
    background: #0f172a;
    color: white;
    padding: 14px;
    border-radius: 12px;
    margin-bottom: 10px;
    border-left: 4px solid #10b981;
}

.message-title {
    font-weight: bold;
    margin-bottom: 6px;
}
</style>
""", unsafe_allow_html=True)

for msg in chat_history:

    if msg["is_user"] == 1:

        st.markdown(
            f"""
            <div class="user-message">
                <div class="message-title">
                    👤 You
                </div>
                <div>
                    {msg["message"]}
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

    else:

        st.markdown(
            f"""
            <div class="assistant-message">
                <div class="message-title">
                    🧞 EduGenie AI
                </div>
                <div>
                    {msg["message"]}
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )
            
            # Form or Chat Input
            user_question = st.text_input(
                "Ask your study genie:",
                placeholder="e.g., What are the main concepts in this chapter?",
                key="input_question"
            )
            
            col_ask, col_clear = st.columns([6, 1])
            with col_ask:
                if st.button("Ask Genie", key="btn_ask", use_container_width=True):
                    if user_question.strip():
                        # Save user question in DB
                        save_chat_message(user_id, user_question, is_user=True)
                        
                        # Generate answer via pipeline
                        with st.spinner("Genie is thinking..."):
                            try:
                                answer = pipeline.ask(user_question, user_id)
                                # Save assistant answer in DB
                                save_chat_message(user_id, answer, is_user=False)
                                st.rerun()
                            except Exception as e:
                                st.error(f"Failed to generate answer: {e}")
                    else:
                        st.warning("Please enter a question.")
            with col_clear:
                if st.button("Clear Chat", key="btn_clear_chat", use_container_width=True):
                    clear_chat_history(user_id)
                    st.success("Chat history cleared!")
                    st.rerun()
                    
        with tab_notes:
            st.write("### Compile Structured Review Notes")
            st.write("Let Gemini analyze the entire document and compile a structured, detailed study guide including definitions, summary points, and takeaways.")
            
            if st.button("Create & Save Notes", key="btn_notes", use_container_width=True):
                with st.spinner("Analyzing document and creating summary notes..."):
                    try:
                        notes = pipeline.generate_notes()
                        # Save notes to database history
                        note_title = f"Review Notes: {active_doc_name}"
                        if save_note(user_id, note_title, notes):
                            st.success("✅ Notes compiled and saved to your dashboard library!")
                        else:
                            st.warning("Notes compiled but failed to save to database history.")
                        
                        st.write("---")
                        st.markdown(f"### {note_title}")
                        st.markdown(notes)
                    except Exception as e:
                        st.error(f"Failed to compile study notes: {e}")
    else:
        if total_docs > 0:
            st.info("👈 Please select a document from the sidebar to activate the Study Assistant features.")
else:
    st.error("Please configure the API key in settings page to run RAG queries.")
