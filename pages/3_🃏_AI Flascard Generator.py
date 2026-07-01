import streamlit as st
import os
import logging
from pathlib import Path
from src.config import validate_config
from src.database.db_manager import (
    get_user_documents, get_flashcards, mark_flashcard_learned,
    delete_all_flashcards, get_db_connection
)
from src.utils.auth_helper import require_login, logout_user
from src.utils.gamification_helper import add_xp, update_streak, award_badge

# Protect page - Redirect to login if unauthorized
require_login()

user_id = st.session_state.user_id
username = st.session_state.username

# Configure page
st.set_page_config(
    page_title="AI Flashcards - EduGenie AI",
    page_icon="🃏",
    layout="wide"
)

# Load external custom styling
def load_css(css_file_path: Path):
    if css_file_path.exists():
        with open(css_file_path, "r", encoding="utf-8") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

css_path = Path(__file__).resolve().parent.parent / "src" / "ui" / "styles.css"
load_css(css_path)

st.markdown("<h1 class='main-title'>🃏 AI Flashcards</h1>", unsafe_allow_html=True)
st.markdown("<p class='subtitle'>Accelerate your memory with auto-generated active recall flashcards from your textbook chapters.</p>", unsafe_allow_html=True)

# Validate configuration
api_key_valid = True
try:
    validate_config()
except ValueError as e:
    api_key_valid = False
    st.warning("")
    

# Retrieve user documents
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
            
        selected_doc = st.selectbox("Select active document:", doc_options, index=default_idx, key="flashcards_select_doc")
        
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

# Check flashcard deck state
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
        
        # Retrieve cards from DB
        cards = get_flashcards(user_id, active_doc_name)
        total_cards = len(cards)
        learned_cards = sum(1 for c in cards if c["learned"] == 1)
        active_cards = total_cards - learned_cards
        
        if total_cards == 0:
            # Render deck generation screen
            st.markdown(
                """
                <div class="feature-card" style="margin-top: 1.5rem; text-align: center; padding: 2rem;">
                    <div style="font-size: 3rem; margin-bottom: 1rem;">🃏</div>
                    <h3>No Flashcards Generated Yet</h3>
                    <p style="color: #94a3b8; max-width: 600px; margin: 0 auto 1.5rem;">
                        EduGenie AI can analyze your study document and generate custom interactive flashcards containing questions, key definitions, and explanations.
                    </p>
                </div>
                """, 
                unsafe_allow_html=True
            )
            
            num_cards = st.slider(
                "Select number of flashcards to generate:",
                min_value=5,
                max_value=20,
                value=10,
                step=1,
                key="flashcard_count_slider"
            )
            
            if st.button("✨ Generate Flashcards using Azure OpenAI", key="btn_generate_cards", use_container_width=True):
                with st.spinner("Analyzing document content and crafting flashcards..."):
                    try:
                        count = pipeline.generate_and_save_flashcards(user_id, active_doc_name, num_cards)
                        if count > 0:
                            # Award XP for generating a schedule/planner (or deck)
                            res = add_xp(user_id, 50)
                            st.toast(f"🎉 Flashcards generated! +50 XP earned.")
                            if res.get("level_up"):
                                st.success(f"🎊 Level Up! You reached Level {res['new_level']}!")
                            st.rerun()
                        else:
                            st.error("No flashcards were generated. Please check document content and try again.")
                    except Exception as e:
                        st.error(f"Failed to generate flashcards: {e}")
        else:
            # Cards exist! Let's display stats and controls
            
            # Progress tracking variables
            progress_pct = int(learned_cards * 100 / total_cards) if total_cards > 0 else 0
            
            # Metric row
            col_m1, col_m2, col_m3 = st.columns(3)
            with col_m1:
                st.markdown(f"""
                <div class="feature-card" style="text-align: center; padding: 1rem 0.5rem; margin-bottom: 0.5rem;">
                    <div style="font-size: 1.6rem; font-weight: 700; color: #4D96FF; margin-bottom: 0.1rem;">{total_cards}</div>
                    <div style="font-size: 0.85rem; color: #b0b0b0;">Total Flashcards</div>
                </div>
                """, unsafe_allow_html=True)
            with col_m2:
                st.markdown(f"""
                <div class="feature-card" style="text-align: center; padding: 1rem 0.5rem; margin-bottom: 0.5rem;">
                    <div style="font-size: 1.6rem; font-weight: 700; color: #6BCB77; margin-bottom: 0.1rem;">{learned_cards}</div>
                    <div style="font-size: 0.85rem; color: #b0b0b0;">Learned Cards</div>
                </div>
                """, unsafe_allow_html=True)
            with col_m3:
                st.markdown(f"""
                <div class="feature-card" style="text-align: center; padding: 1rem 0.5rem; margin-bottom: 0.5rem;">
                    <div style="font-size: 1.6rem; font-weight: 700; color: #FF6B6B; margin-bottom: 0.1rem;">{active_cards}</div>
                    <div style="font-size: 0.85rem; color: #b0b0b0;">Active/Reviewing Cards</div>
                </div>
                """, unsafe_allow_html=True)
            
            # Progress Bar (Premium Design)
            st.markdown(f"""
            <div style="margin-bottom: 2rem;">
                <div style="display: flex; justify-content: space-between; font-size: 0.85rem; margin-bottom: 0.4rem; color: #94a3b8;">
                    <span>Deck Mastery Progress</span>
                    <span>{learned_cards}/{total_cards} learned ({progress_pct}%)</span>
                </div>
                <div style="background: rgba(255,255,255,0.05); border-radius: 10px; height: 10px; width: 100%; overflow: hidden; border: 1px solid rgba(255,255,255,0.05);">
                    <div style="background: linear-gradient(90deg, #8B5CF6 0%, #3B82F6 100%); height: 100%; width: {progress_pct}%; transition: width 0.4s ease;"></div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            tab_review, tab_deck_mgr = st.tabs(["👁️ Review Mode", "⚙️ Deck Management"])
            
            with tab_review:
                # Session state initialization for card index
                if "flashcard_idx" not in st.session_state:
                    st.session_state.flashcard_idx = 0
                if "card_flipped" not in st.session_state:
                    st.session_state.card_flipped = False
                
                # Boundary check
                if st.session_state.flashcard_idx >= total_cards:
                    st.session_state.flashcard_idx = 0
                if st.session_state.flashcard_idx < 0:
                    st.session_state.flashcard_idx = total_cards - 1
                    
                idx = st.session_state.flashcard_idx
                current_card = cards[idx]
                
                # Glassmorphism HTML/CSS Flip Card Rendering
                flipped_class = "flipped" if st.session_state.card_flipped else ""
                learned_badge = '<span class="status-badge badge-active" style="position: absolute; top: 15px; left: 15px; z-index: 10;">Learned ✓</span>' if current_card['learned'] == 1 else '<span class="status-badge badge-inactive" style="position: absolute; top: 15px; left: 15px; z-index: 10;">Active Review</span>'
                
                st.markdown(
                    f"""
                    <style>
                    .flashcard-container {{
                        perspective: 1000px;
                        width: 100%;
                        max-width: 650px;
                        height: 320px;
                        margin: 20px auto;
                        cursor: pointer;
                    }}
                    .flashcard-inner {{
                        position: relative;
                        width: 100%;
                        height: 100%;
                        text-align: center;
                        transition: transform 0.5s cubic-bezier(0.4, 0, 0.2, 1);
                        transform-style: preserve-3d;
                        border-radius: 18px;
                    }}
                    .flashcard-container.flipped .flashcard-inner {{
                        transform: rotateY(180deg);
                    }}
                    .flashcard-front, .flashcard-back {{
                        position: absolute;
                        width: 100%;
                        height: 100%;
                        backface-visibility: hidden;
                        display: flex;
                        flex-direction: column;
                        align-items: center;
                        justify-content: center;
                        padding: 30px;
                        box-sizing: border-box;
                        border-radius: 18px;
                        box-shadow: 0 10px 35px 0 rgba(0, 0, 0, 0.4);
                        border: 1px solid rgba(255, 255, 255, 0.07);
                    }}
                    .flashcard-front {{
                        background: rgba(30, 41, 59, 0.6);
                        color: #F8FAFC;
                    }}
                    .flashcard-back {{
                        background: rgba(139, 92, 246, 0.12);
                        color: #F8FAFC;
                        transform: rotateY(180deg);
                        border-color: rgba(139, 92, 246, 0.35);
                    }}
                    .flashcard-type {{
                        font-size: 0.8rem;
                        color: #94a3b8;
                        text-transform: uppercase;
                        letter-spacing: 0.15em;
                        margin-bottom: 12px;
                        font-weight: 600;
                    }}
                    .flashcard-text {{
                        font-size: 1.35rem;
                        font-weight: 500;
                        line-height: 1.5;
                    }}
                    </style>
                    
                    <div class="flashcard-container {flipped_class}">
                        <div class="flashcard-inner">
                            <div class="flashcard-front">
                                {learned_badge}
                                <div class="flashcard-type">Question</div>
                                <div class="flashcard-text">{current_card['question']}</div>
                                <div style="margin-top: 20px; font-size: 0.8rem; color: #94a3b8;">Click Reveal Answer below to flip</div>
                            </div>
                            <div class="flashcard-back">
                                {learned_badge}
                                <div class="flashcard-type" style="color: #a78bfa;">Answer</div>
                                <div class="flashcard-text">{current_card['answer']}</div>
                                <div style="margin-top: 20px; font-size: 0.8rem; color: #94a3b8;">Click Hide Answer below to flip back</div>
                            </div>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
                
                # Navigation Controls row
                col_btn_prev, col_btn_flip, col_btn_next = st.columns([1, 2, 1])
                with col_btn_prev:
                    if st.button("⬅️ Previous", key="btn_card_prev", use_container_width=True):
                        st.session_state.flashcard_idx = (idx - 1) % total_cards
                        st.session_state.card_flipped = False
                        st.rerun()
                with col_btn_flip:
                    flip_label = "Hide Answer 👁️" if st.session_state.card_flipped else "Reveal Answer 👁️"
                    if st.button(flip_label, key="btn_card_flip", use_container_width=True):
                        st.session_state.card_flipped = not st.session_state.card_flipped
                        st.rerun()
                with col_btn_next:
                    if st.button("Next ➡️", key="btn_card_next", use_container_width=True):
                        st.session_state.flashcard_idx = (idx + 1) % total_cards
                        st.session_state.card_flipped = False
                        st.rerun()
                
                # Card Action Buttons (Mark Learned / Unlearned)
                if st.session_state.card_flipped:
                    st.write("")
                    col_act_l, col_act_r = st.columns(2)
                    with col_act_l:
                        is_learned = current_card["learned"] == 1
                        lbl = "Mark Learned ✅" if not is_learned else "Already Learned ✓"
                        if st.button(lbl, key="btn_mark_learned", disabled=is_learned, use_container_width=True):
                            if mark_flashcard_learned(user_id, current_card["id"], 1):
                                # Award +15 XP for learning a card!
                                xp_res = add_xp(user_id, 15)
                                update_streak(user_id)
                                
                                # Check badge condition
                                conn = get_db_connection()
                                cursor = conn.cursor()
                                cursor.execute("SELECT COUNT(*) FROM flashcards WHERE user_id = ? AND learned = 1", (user_id,))
                                total_learned_all_decks = cursor.fetchone()[0]
                                conn.close()
                                
                                badge_toast = ""
                                if total_learned_all_decks >= 10:
                                    if award_badge(user_id, "🃏 Memorizer"):
                                        badge_toast = " 🏆 Unlocked Badge: Memorizer!"
                                        
                                st.toast(f"🎉 Card learned! +15 XP earned.{badge_toast}")
                                if xp_res.get("level_up"):
                                    st.success(f"🎊 Level Up! You reached Level {xp_res['new_level']}!")
                                
                                st.rerun()
                    with col_act_r:
                        is_active = current_card["learned"] == 0
                        lbl = "Mark Active / Reviewing 🔄" if not is_active else "Already Active 🔄"
                        if st.button(lbl, key="btn_mark_active", disabled=is_active, use_container_width=True):
                            if mark_flashcard_learned(user_id, current_card["id"], 0):
                                st.toast("Card marked as active.")
                                st.rerun()
                
                st.caption(f"<div style='text-align:center; color:#94a3b8;'>Card {idx + 1} of {total_cards}</div>", unsafe_allow_html=True)
            
            with tab_deck_mgr:
                st.write("### Deck Configurations & Management")
                
                col_dm1, col_dm2 = st.columns(2)
                with col_dm1:
                    st.write("Need different flashcards, or want to expand your deck? You can delete this deck and generate a new one from scratch.")
                    if st.button("⚠️ Delete Current Deck", key="btn_delete_deck", use_container_width=True):
                        with st.spinner("Deleting flashcards..."):
                            if delete_all_flashcards(user_id, active_doc_name):
                                st.success("Deck deleted successfully!")
                                st.session_state.flashcard_idx = 0
                                st.session_state.card_flipped = False
                                st.rerun()
                with col_dm2:
                    st.write("Regenerate the deck content right away. This replaces the existing card list with fresh ones.")
                    if st.button("🔄 Regenerate Deck", key="btn_regen_deck", use_container_width=True):
                        with st.spinner("Re-generating flashcards..."):
                            try:
                                count = pipeline.generate_and_save_flashcards(user_id, active_doc_name, total_cards)
                                if count > 0:
                                    st.success(f"Regenerated {count} cards!")
                                    st.session_state.flashcard_idx = 0
                                    st.session_state.card_flipped = False
                                    st.rerun()
                            except Exception as e:
                                st.error(f"Regeneration failed: {e}")
                                
                st.write("---")
                st.write("#### Flashcards Reference Directory")
                
                # Show cards in a clean table representation
                import pandas as pd
                records = []
                for c in cards:
                    records.append({
                        "ID": c["id"],
                        "Question": c["question"],
                        "Answer": c["answer"],
                        "Status": "Learned" if c["learned"] == 1 else "Active Review"
                    })
                df = pd.DataFrame(records)
                st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("👋 No active study document loaded. Please upload a PDF or select an active document in the sidebar study library.")
else:
    st.error("Please configure the API key in settings page to generate flashcards.")
