import streamlit as st
import os
import logging
from pathlib import Path
from src.config import validate_config
from src.database.db_manager import get_user_documents, save_quiz_record
from src.utils.auth_helper import require_login, logout_user

# Set up logging
logger = logging.getLogger(__name__)

# 1. Protect page - Redirect to login if unauthorized
require_login()

user_id = st.session_state.user_id
username = st.session_state.username

# Configure page
st.set_page_config(
    page_title="Quiz Generator - EduGenie AI",
    page_icon="📝",
    layout="wide"
)

# Load external custom styling
def load_css(css_file_path: Path):
    if css_file_path.exists():
        with open(css_file_path, "r", encoding="utf-8") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

css_path = Path(__file__).resolve().parent.parent / "src" / "ui" / "styles.css"
load_css(css_path)

st.markdown("<h1 class='main-title'>📝 Quiz Generator</h1>", unsafe_allow_html=True)
st.markdown("<p class='subtitle'>Test your comprehension with interactive multiple-choice quizzes automatically generated from your syllabus.</p>", unsafe_allow_html=True)

# 2. Validate configuration
api_key_valid = True
try:
    validate_config()
except ValueError as e:
    api_key_valid = False
    st.warning("⚠️ Azure OpenAI configuration is incomplete.")
    st.info(
        "Please configure Azure OpenAI Endpoint, API Key, Deployment Name, and API Version in Settings."
    )
# 3. Retrieve user documents
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
            
        selected_doc = st.selectbox("Select active document:", doc_options, index=default_idx, key="quiz_select_doc")
        
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

# Main page logic
if api_key_valid:
    pipeline = st.session_state.get("pipeline")
    active_doc_name = st.session_state.get("active_document_name")
    
    if active_doc_name and pipeline:
        # Load active document path if not set in pipeline
        if not pipeline.current_pdf_path:
            matching_docs = [d for d in user_docs if d["file_name"] == active_doc_name]
            if matching_docs:
                pipeline.current_pdf_path = Path(matching_docs[0]["file_path"])
                
        st.markdown(f"#### Active Document: **{active_doc_name}**")
        
        # 4. Check if a quiz is already in session state
        if "current_quiz" not in st.session_state:
            st.write("### Configure assessment length and generate questions")
            num_questions = st.slider(
                "Select the number of questions to generate:",
                min_value=3,
                max_value=10,
                value=5,
                step=1,
                help="Choose the length of your multiple-choice test."
            )
            
            if st.button("Generate Quiz", key="btn_gen_quiz", use_container_width=True):
                with st.spinner(f"Analyzing '{active_doc_name}' and creating structured quiz..."):
                    try:
                        quiz_data = pipeline.generate_quiz_structured(num_questions)
                        if quiz_data and quiz_data.questions:
                            st.session_state.current_quiz = quiz_data.questions
                            st.session_state.quiz_answers = {}
                            st.session_state.quiz_submitted = False
                            st.session_state.quiz_num_questions = len(quiz_data.questions)
                            st.rerun()
                        else:
                            st.error("No questions could be generated. Try a different document.")
                    except Exception as e:
                        st.error(f"Failed to generate structured quiz: {e}")
        else:
            # A quiz is active in session state!
            questions = st.session_state.current_quiz
            total_q = st.session_state.quiz_num_questions
            submitted = st.session_state.quiz_submitted
            
            st.write("---")
            st.write(f"### Interactive Quiz ({total_q} questions)")
            
            # Form for selecting answers
            with st.form("quiz_form"):
                user_selections = {}
                for idx, q in enumerate(questions):
                    st.markdown(f"#### Q{idx + 1}. {q.question}")
                    
                    # Map choices: A, B, C, D
                    letters = ["A", "B", "C", "D"]
                    options_labels = []
                    for i, opt in enumerate(q.options):
                        lbl = opt.strip()
                        # Clean label prefixes if they already contain letter prefix
                        if not (lbl.startswith("A)") or lbl.startswith("B)") or lbl.startswith("C)") or lbl.startswith("D)") or
                                lbl.startswith("A.") or lbl.startswith("B.") or lbl.startswith("C.") or lbl.startswith("D.")):
                            lbl = f"{letters[i]}) {lbl}"
                        options_labels.append(lbl)
                    
                    # Fill options
                    default_choice = None
                    if idx in st.session_state.quiz_answers:
                        default_choice = st.session_state.quiz_answers[idx]
                        
                    # Radio selection
                    selected_label = st.radio(
                        "Choose the correct option:",
                        options_labels,
                        index=options_labels.index(default_choice) if default_choice in options_labels else 0,
                        key=f"q_radio_{idx}",
                        label_visibility="collapsed"
                    )
                    
                    # Save selected letter
                    selected_letter = selected_label[0]  # E.g. "A"
                    user_selections[idx] = {
                        "letter": selected_letter,
                        "label": selected_label
                    }
                    
                # Submit form button
                form_btn_label = "Submit Answers" if not submitted else "Results Submitted"
                form_submit = st.form_submit_button(form_btn_label, disabled=submitted, use_container_width=True)
                
                if form_submit:
                    # Save selections in session state
                    for idx, sel in user_selections.items():
                        st.session_state.quiz_answers[idx] = sel["label"]
                    
                    # Compute score
                    score = 0
                    for idx, q in enumerate(questions):
                        ans_letter = user_selections[idx]["letter"]
                        if ans_letter == q.correct_answer:
                            score += 1
                    
                    # Save score in SQLite DB
                    save_quiz_record(user_id, active_doc_name, score, total_q)
                    st.session_state.quiz_submitted = True
                    st.session_state.quiz_score = score
                    st.rerun()
            
            # Display results if submitted
            if submitted:
                score = st.session_state.quiz_score
                pct = int(score * 100 / total_q)
                
                # Display Score Badge
                st.write("---")
                if pct >= 80:
                    st.success(f"🎉 **Great job!** You scored **{score}/{total_q} ({pct}%)**")
                elif pct >= 50:
                    st.warning(f"🔔 **Good effort!** You scored **{score}/{total_q} ({pct}%)**")
                else:
                    st.error(f"📚 **Keep studying!** You scored **{score}/{total_q} ({pct}%)**")
                    
                # Reveal explanations and highlights
                for idx, q in enumerate(questions):
                    selected_lbl = st.session_state.quiz_answers.get(idx, "None")
                    selected_letter = selected_lbl[0] if selected_lbl != "None" else "None"
                    
                    is_correct = (selected_letter == q.correct_answer)
                    
                    st.markdown(f"#### Q{idx + 1}. {q.question}")
                    
                    # Display options with color coding
                    for i, opt in enumerate(q.options):
                        letter = letters[i]
                        lbl = opt.strip()
                        if not (lbl.startswith("A)") or lbl.startswith("B)") or lbl.startswith("C)") or lbl.startswith("D)") or
                                lbl.startswith("A.") or lbl.startswith("B.") or lbl.startswith("C.") or lbl.startswith("D.")):
                            lbl = f"{letter}) {lbl}"
                            
                        # Format option colors
                        if letter == q.correct_answer:
                            st.markdown(f"<span style='color:#6BCB77; font-weight:bold;'>✓ {lbl} (Correct Option)</span>", unsafe_allow_html=True)
                        elif letter == selected_letter and not is_correct:
                            st.markdown(f"<span style='color:#FF6B6B; font-weight:bold;'>✗ {lbl} (Your Choice - Incorrect)</span>", unsafe_allow_html=True)
                        else:
                            st.markdown(f"<span style='color:#a0a0a0;'>&nbsp;&nbsp;{lbl}</span>", unsafe_allow_html=True)
                            
                    st.info(f"💡 **Explanation:** {q.explanation}")
                    st.markdown("---")
                    
                # New Quiz button
                if st.button("Take Another Quiz", key="btn_clear_quiz", use_container_width=True):
                    del st.session_state["current_quiz"]
                    del st.session_state["quiz_answers"]
                    del st.session_state["quiz_submitted"]
                    if "quiz_score" in st.session_state:
                        del st.session_state["quiz_score"]
                    st.rerun()
    else:
        st.info("👋 No active study document loaded. Please upload a PDF or select an active document in the sidebar study library.")
else:
    st.error(
    "Please configure Azure OpenAI credentials in Settings before generating quizzes."
    )