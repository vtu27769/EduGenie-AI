import streamlit as st

def card(title: str, text: str, icon: str = ""):
    """
    Renders a custom HTML/CSS card components for premium styling.
    """
    st.markdown(f"""
    <div class="feature-card">
        <div class="card-title">{icon} {title}</div>
        <div class="card-text">{text}</div>
    </div>
    """, unsafe_allow_html=True)
