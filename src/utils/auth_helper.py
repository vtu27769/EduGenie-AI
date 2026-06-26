import streamlit as st
import logging
from streamlit_cookies_controller import CookieController
from src.database.db_manager import get_user_by_token

logger = logging.getLogger(__name__)

def init_auth():
    """
    Initializes user session. Checks if logged in or has a remember_token cookie.
    """
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
        st.session_state.user_id = None
        st.session_state.username = None

    if not st.session_state.logged_in:
        try:
            controller = CookieController()
            token = controller.get("remember_token")
            if token:
                logger.info("Found remember_token cookie. Validating...")
                user = get_user_by_token(token)
                if user:
                    st.session_state.logged_in = True
                    st.session_state.user_id = user["id"]
                    st.session_state.username = user["username"]
                    
                    # Lazy init RAGPipeline if needed
                    from src.rag.pipeline import RAGPipeline
                    if "pipeline" not in st.session_state:
                        try:
                            st.session_state.pipeline = RAGPipeline()
                        except Exception as e:
                            logger.error(f"Failed to initialize RAG Pipeline: {e}")
                    
                    logger.info(f"Auto-login successful for user: {user['username']}")
                    st.rerun()
        except Exception as e:
            # Silently catch cookie read errors if the streamlit component hasn't loaded yet
            pass

def require_login():
    """
    Protects a page by verifying authentication state.
    Redirects to app.py if not logged in.
    """
    # Run initialization checks
    init_auth()
    
    if not st.session_state.logged_in:
        st.warning("🔒 Access Denied. Please log in to access this module.")
        st.switch_page("app.py")
        st.stop()

def logout_user():
    """
    Logs out the user, clears session states, and clears remember_token cookie.
    """
    user_id = st.session_state.get("user_id")
    if user_id:
        from src.database.db_manager import update_remember_token
        # Invalidate token in DB
        update_remember_token(user_id, generate=False)
        
    try:
        controller = CookieController()
        controller.remove("remember_token")
    except Exception as e:
        logger.error(f"Failed to remove remember_token cookie: {e}")
        
    # Clear session state keys
    st.session_state.logged_in = False
    st.session_state.user_id = None
    st.session_state.username = None
    if "pipeline" in st.session_state:
        del st.session_state["pipeline"]
    if "active_document_name" in st.session_state:
        del st.session_state["active_document_name"]
        
    st.success("You have been logged out successfully.")
    st.switch_page("app.py")
    st.stop()
