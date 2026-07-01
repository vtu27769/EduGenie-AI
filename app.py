import streamlit as st
import os
import logging
from pathlib import Path
from src.config import UPLOAD_DIR, validate_config
from src.database.db_manager import (
    init_db, register_user, authenticate_user, get_user_by_username,
    reset_password, update_remember_token, add_uploaded_document,
    get_user_documents, delete_uploaded_document, get_user_quiz_history,
    get_user_notes, check_password, hash_password
)
from src.utils.auth_helper import init_auth, logout_user
from streamlit_cookies_controller import CookieController
import sys
import streamlit as st

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize database schema
init_db()

# Configure page settings
st.set_page_config(
    page_title="EduGenie AI - Intelligent Study Dashboard",
    page_icon="🧞",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Load external CSS styles
def load_css(css_file_path: Path):
    if css_file_path.exists():
        with open(css_file_path, "r", encoding="utf-8") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

css_path = Path(__file__).resolve().parent / "src" / "ui" / "styles.css"
load_css(css_path)

# Initialize Session State Auth and Cookie Check
init_auth()

# Main Header / Styling wrapper
st.markdown("<h1 class='main-title'>EduGenie AI 🧞</h1>", unsafe_allow_html=True)

# ----------------- AUTHENTICATION INTERFACE -----------------
if not st.session_state.logged_in:
    st.markdown("<p class='subtitle'>Transform your study documents into interactive quizzes, structured notes, and answers instantly.</p>", unsafe_allow_html=True)
    
    col_l, col_c, col_r = st.columns([1, 2, 1])
    
    with col_c:
        tab_login, tab_register, tab_forgot = st.tabs(["🔑 Login", "📝 Register", "🔒 Forgot Password"])
        
        # 1. Login Tab
        with tab_login:
            st.markdown("### Welcome Back!")
            login_username = st.text_input("Username", key="login_user", placeholder="Enter your username...")
            login_password = st.text_input("Password", type="password", key="login_pass", placeholder="Enter your password...")
            remember_me = st.checkbox("Remember Me", key="login_remember", help="Stay logged in on this browser.")
            
            if st.button("Log In", key="btn_login_submit", use_container_width=True):
                if not login_username.strip() or not login_password.strip():
                    st.error("Please enter both username and password.")
                else:
                    with st.spinner("Authenticating..."):
                        user = authenticate_user(login_username, login_password)
                        if user:
                            st.session_state.logged_in = True
                            st.session_state.user_id = user["id"]
                            st.session_state.username = user["username"]
                            # Initialize RAG pipeline
                            from src.rag.pipeline import RAGPipeline
                            if "pipeline" not in st.session_state:
                                try:
                                    st.session_state.pipeline = RAGPipeline()
                                except Exception as e:
                                    logger.error(f"Failed to load pipeline: {e}")
                            
                            # Set Remember Me token if selected
                            if remember_me:
                                token = update_remember_token(user["id"], generate=True)
                                if token:
                                    try:
                                        controller = CookieController()
                                        controller.set("remember_token", token)
                                    except Exception as e:
                                        logger.error(f"Failed to set remember_token cookie: {e}")
                                        
                            st.success(f"🎉 Success! Welcome back, {user['username']}.")
                            st.rerun()
                        else:
                            st.error("Incorrect username or password. Please try again.")
                            
        # 2. Register Tab
        with tab_register:
            st.markdown("### Create an Account")
            reg_username = st.text_input("Choose Username", key="reg_user", placeholder="Must be unique...")
            reg_password = st.text_input("Password", type="password", key="reg_pass", placeholder="Choose a strong password...")
            reg_confirm = st.text_input("Confirm Password", type="password", key="reg_pass_confirm", placeholder="Re-enter password...")
            
            security_q_list = [
                "What is your mother's maiden name?",
                "What was the name of your first pet?",
                "In what city were you born?",
                "What was the name of your elementary school?",
                "What is your favorite book?"
            ]
            reg_question = st.selectbox("Select Security Question", security_q_list, key="reg_q_select")
            reg_answer = st.text_input("Security Answer", key="reg_ans_input", placeholder="Used for password recovery...")
            
            if st.button("Create Account", key="btn_register_submit", use_container_width=True):
                if not reg_username.strip() or not reg_password.strip() or not reg_answer.strip():
                    st.error("All fields are required.")
                elif reg_password != reg_confirm:
                    st.error("Passwords do not match.")
                elif len(reg_password) < 6:
                    st.error("Password must be at least 6 characters long.")
                else:
                    with st.spinner("Creating account..."):
                        success = register_user(reg_username, reg_password, reg_question, reg_answer)
                        if success:
                            st.success("✅ Account created successfully! Please switch to the Login tab.")
                        else:
                            st.error("Username is already taken. Please choose another one.")
                            
        # 3. Forgot Password Tab
        with tab_forgot:
            st.markdown("### Recover Your Account")
            
            # Step 1: Username lookup
            lookup_username = st.text_input("Enter Username", key="lookup_user", placeholder="Enter your username to look up...")
            
            if lookup_username.strip():
                user_info = get_user_by_username(lookup_username)
                if user_info:
                    st.success(f"Security Question: **{user_info['security_question']}**")
                    
                    recover_answer = st.text_input("Security Answer", type="password", key="recover_ans", placeholder="Enter security answer...")
                    new_password = st.text_input("New Password", type="password", key="recover_pwd", placeholder="Minimum 6 characters...")
                    new_password_confirm = st.text_input("Confirm New Password", type="password", key="recover_pwd_confirm", placeholder="Re-enter new password...")
                    
                    if st.button("Reset Password", key="btn_reset_submit", use_container_width=True):
                        if not recover_answer.strip() or not new_password.strip():
                            st.error("Please fill in all recovery fields.")
                        elif new_password != new_password_confirm:
                            st.error("New passwords do not match.")
                        elif len(new_password) < 6:
                            st.error("Password must be at least 6 characters long.")
                        else:
                            # Verify security answer
                            if check_password(recover_answer.strip().lower(), user_info["security_answer_hash"]):
                                # Answer verified, reset password
                                if reset_password(user_info["id"], new_password):
                                    st.success("🎉 Password reset successfully! You can now log in with your new password.")
                                else:
                                    st.error("Failed to update password. Please contact support.")
                            else:
                                st.error("❌ Incorrect security answer. Reset failed.")
                else:
                    st.error("No user found with that username.")
            else:
                st.caption("Please enter your username to view your security question.")

# ----------------- AUTHENTICATED USER DASHBOARD -----------------
else:
    # Set up pipeline if not in session state (in case of page reloads)
    from src.rag.pipeline import RAGPipeline
    if "pipeline" not in st.session_state:
        try:
            st.session_state.pipeline = RAGPipeline()
        except Exception as e:
            logger.error(f"Failed to initialize the RAG system: {e}")
            st.error("RAG pipeline failed to initialize. Azure features might be unavailable.")

    user_id = st.session_state.user_id
    username = st.session_state.username
    
    st.markdown(f"<p class='subtitle'>Welcome back, <b>{username}</b>! Let's power up your learning journey today.</p>", unsafe_allow_html=True)
    
    # 1. Fetch user data statistics
    user_docs = get_user_documents(user_id)
    user_quizzes = get_user_quiz_history(user_id)
    user_notes = get_user_notes(user_id)
    
    total_docs = len(user_docs)
    total_quizzes = len(user_quizzes)
    avg_score = 0
    if total_quizzes > 0:
        avg_score = int(sum([q["score"] * 100 / q["total_questions"] for q in user_quizzes]) / total_quizzes)
    total_saved_notes = len(user_notes)
    
    # 2. Render Metrics Cards
    m_col1, m_col2, m_col3 = st.columns(3)
    with m_col1:
        st.markdown(f"""
        <div class="feature-card" style="text-align: center; padding: 1rem 0.5rem; margin-bottom: 1rem;">
            <div style="font-size: 2.2rem; margin-bottom: 0.3rem;">📄</div>
            <div style="font-size: 1.8rem; font-weight: 700; color: #4D96FF; margin-bottom: 0.1rem;">{total_docs}</div>
            <div style="font-size: 0.9rem; color: #b0b0b0;">Uploaded Study Materials</div>
        </div>
        """, unsafe_allow_html=True)
        
    with m_col2:
        st.markdown(f"""
        <div class="feature-card" style="text-align: center; padding: 1rem 0.5rem; margin-bottom: 1rem;">
            <div style="font-size: 2.2rem; margin-bottom: 0.3rem;">🎯</div>
            <div style="font-size: 1.8rem; font-weight: 700; color: #6BCB77; margin-bottom: 0.1rem;">{avg_score}% ({total_quizzes} tests)</div>
            <div style="font-size: 0.9rem; color: #b0b0b0;">Average Quiz Score</div>
        </div>
        """, unsafe_allow_html=True)
        
    with m_col3:
        st.markdown(f"""
        <div class="feature-card" style="text-align: center; padding: 1rem 0.5rem; margin-bottom: 1rem;">
            <div style="font-size: 2.2rem; margin-bottom: 0.3rem;">📝</div>
            <div style="font-size: 1.8rem; font-weight: 700; color: #FF6B6B; margin-bottom: 0.1rem;">{total_saved_notes}</div>
            <div style="font-size: 0.9rem; color: #b0b0b0;">Generated Study Guides</div>
        </div>
        """, unsafe_allow_html=True)
        
    st.markdown("---")
    
    # 3. Main Dashboard Body
    dash_col_left, dash_col_right = st.columns([1, 1])
    
    with dash_col_left:
        st.markdown("### 📤 Document Upload Center")
        st.write("Upload course syllabi, lecture slides, notes, or books (PDF) to build your personalized RAG knowledge base.")
        
        # Check API key configuration status
    

        api_key_valid = True
        if api_key_valid:
            # File Uploader
            dashboard_file = st.file_uploader(
                "Select a PDF file to index:",
                type=["pdf"],
                key="dashboard_uploader",
                help="Only PDF formatted files are supported."
            )
            
            if dashboard_file is not None:
                # Calculate if file is already indexed
                already_indexed = any(doc["file_name"] == dashboard_file.name for doc in user_docs)
                if not already_indexed:
                    with st.spinner(f"Processing and embedding '{dashboard_file.name}'..."):
                        try:
                            # Create user directory if it doesn't exist
                            user_upload_dir = UPLOAD_DIR / f"user_{user_id}"
                            user_upload_dir.mkdir(parents=True, exist_ok=True)
                            
                            saved_path = user_upload_dir / dashboard_file.name
                            with open(saved_path, "wb") as f:
                                f.write(dashboard_file.getbuffer())
                            
                            # Run RAG Indexing
                            pipeline = st.session_state.pipeline
                            pipeline.index_pdf(str(saved_path), user_id)
                            
                            # Log document in DB
                            add_uploaded_document(
                                user_id, 
                                dashboard_file.name, 
                                str(saved_path), 
                                dashboard_file.size
                            )
                            
                            # Cache as active document name
                            st.session_state.active_document_name = dashboard_file.name
                            st.success(f"✅ Indexed and saved '{dashboard_file.name}' successfully!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Failed to process document: {e}")
                else:
                    st.info("ℹ️ This file is already in your study library.")
        
        st.write("#### 📚 Your Study Library")
        if total_docs > 0:
            for idx, doc in enumerate(user_docs):
                doc_card = st.container()
                with doc_card:
                    c_file, c_act = st.columns([4, 1])
                    with c_file:
                        # Mark active document
                        is_active = st.session_state.get("active_document_name") == doc["file_name"]
                        lbl = f"⭐ **{doc['file_name']}** (Active)" if is_active else doc["file_name"]
                        st.markdown(f"📄 {lbl}  \n*{round(doc['file_size']/1024, 1)} KB | Uploaded on {doc['upload_time'][:10]}*")
                    with c_act:
                        if st.button("Delete", key=f"del_doc_{doc['id']}_{idx}"):
                            with st.spinner("Deleting..."):
                                deleted_info = delete_uploaded_document(user_id, doc["id"])
                                if deleted_info:
                                    # Physical file cleanup
                                    f_path = Path(deleted_info["file_path"])
                                    if f_path.exists():
                                        os.remove(f_path)
                                    
                                    # Active document cleanup
                                    if st.session_state.get("active_document_name") == deleted_info["file_name"]:
                                        del st.session_state["active_document_name"]
                                        if "pipeline" in st.session_state:
                                            st.session_state.pipeline.current_pdf_path = None
                                            
                                    st.success(f"Deleted '{deleted_info['file_name']}'.")
                                    st.rerun()
        else:
            st.info("No study materials uploaded yet. Upload a PDF above to get started!")

    with dash_col_right:
        st.markdown("### 🎓 Quick Study Navigation")
        
        nav_1, nav_2, nav_3 = st.columns(3)
        with nav_1:
            st.markdown("""
            <div class="feature-card" style="min-height: 120px;">
                <div class="card-title">📖 Study Assistant</div>
                <div style="font-size: 0.85rem; color: #e0e0e0; margin-bottom: 0.8rem;">
                    Chat with your active PDF, ask questions and generate notes.
                </div>
            </div>
            """, unsafe_allow_html=True)
            if st.button("Go to Study Assistant", use_container_width=True):
                st.switch_page("pages/1_📖_AI Tutor.py")
                
        with nav_2:
            st.markdown("""
            <div class="feature-card" style="min-height: 120px;">
                <div class="card-title">📝 Quiz Generator</div>
                <div style="font-size: 0.85rem; color: #e0e0e0; margin-bottom: 0.8rem;">
                    Take auto-generated multiple-choice tests on your syllabus.
                </div>
            </div>
            """, unsafe_allow_html=True)
            if st.button("Go to Quiz Generator", use_container_width=True):
                st.switch_page("pages/2_📝_AI Quiz Generator.py")

        with nav_3:
            st.markdown("""
            <div class="feature-card" style="min-height: 120px;">
                <div class="card-title">🃏 AI Flashcards</div>
                <div style="font-size: 0.85rem; color: #e0e0e0; margin-bottom: 0.8rem;">
                    Generate and review active recall cards to boost retention.
                </div>
            </div>
            """, unsafe_allow_html=True)
            if st.button("Go to AI Flashcards", use_container_width=True):
                st.switch_page("pages/3_🃏_AI Flashcards.py")
                
        st.write("#### 📊 Recent Quiz Activity")
        if total_quizzes > 0:
            import pandas as pd
            records = []
            for record in user_quizzes[:5]:
                pct = int(record["score"] * 100 / record["total_questions"])
                records.append({
                    "Document": record["document_name"],
                    "Score": f"{record['score']}/{record['total_questions']} ({pct}%)",
                    "Date Taken": record["taken_at"][:16]
                })
            df = pd.DataFrame(records)
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.caption("No quiz records yet. Test your knowledge in the Quiz Generator page!")
            
        st.write("#### 📑 Saved Notes & Guides")
        if total_saved_notes > 0:
            for idx, note in enumerate(user_notes[:5]):
                with st.expander(f"📝 {note['title']} ({note['generated_at'][:10]})"):
                    st.markdown(note["content"])
                    if st.button("Delete Note", key=f"del_note_{note['id']}_{idx}"):
                        from src.database.db_manager import delete_note
                        if delete_note(user_id, note["id"]):
                            st.success("Deleted note!")
                            st.rerun()
        else:
            st.caption("No generated study notes saved. Create them inside the Study Assistant tab!")

    # 4. Sidebar Branding & Logout
    with st.sidebar:
        st.image("https://img.icons8.com/clouds/200/genie.png", width=100)
        st.markdown(f"## EduGenie Dashboard")
        st.markdown(f"👤 **User:** `{username}`")
        
        # Display Active Document
        active_doc = st.session_state.get("active_document_name")
        if active_doc:
            st.markdown(f"📄 **Active File:**  \n`{active_doc}`")
        else:
            # If there are uploaded documents, let them pick an active one
            if total_docs > 0:
                doc_options = [doc["file_name"] for doc in user_docs]
                selected_doc = st.selectbox("Select active file:", doc_options, key="sb_active_select")
                if selected_doc:
                    st.session_state.active_document_name = selected_doc
                    # Set the active path in RAGPipeline
                    matching_doc_path = next(doc["file_path"] for doc in user_docs if doc["file_name"] == selected_doc)
                    if "pipeline" in st.session_state:
                        st.session_state.pipeline.current_pdf_path = Path(matching_doc_path)
                    st.rerun()
            else:
                st.info("Please upload a PDF document to start study assistant sessions.")
                
        st.markdown("---")
        
        if st.button("⚙️ Application Settings", use_container_width=True):
            st.switch_page("pages/Settings.py")
            
        if st.button("🚪 Log Out", use_container_width=True):
            logout_user()