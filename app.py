import streamlit as st
from core.database import DatabaseManager
from core.auth import AuthManager
from pages.registration import show_registration_page
from pages.login import show_login_page
from pages.dashboard import show_dashboard
from static.styles import CUSTOM_CSS
import time

# Page configuration
st.set_page_config(
    page_title="CareerVertex - AI CV Analysis",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Apply custom CSS
st.markdown(f"<style>{CUSTOM_CSS}</style>", unsafe_allow_html=True)

# Initialize managers
@st.cache_resource
def init_managers():
    db_manager = DatabaseManager()
    auth_manager = AuthManager(db_manager)
    return db_manager, auth_manager

def main():
    """Main application entry point."""
    db_manager, auth_manager = init_managers()
    
    # Initialize database schema if needed
    if 'db_initialized' not in st.session_state:
        if db_manager.initialize_schema():
            st.session_state.db_initialized = True
        else:
            st.error("Failed to initialize database. Please check configuration.")
            st.stop()
    
    # Check query parameters for login token
    query_params = st.query_params
    if "token" in query_params:
        # Verify login token
        token = query_params["token"]
        user_data = auth_manager.verify_login_token(token)
        if user_data:
            st.session_state.user_id = user_data['user_id']
            st.session_state.user_data = user_data
            st.query_params.clear()
            st.success("Login successful!")
            time.sleep(1)
            st.rerun()
    
    # Route based on authentication state
    if 'user_id' in st.session_state:
        show_dashboard(db_manager, auth_manager)
    else:
        # Show login/registration options
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.markdown("<h1 style='text-align: center;'>Welcome to <span class='gold-gradient'>CareerVertex</span></h1>", unsafe_allow_html=True)
            st.markdown("<p style='text-align: center; font-size: 1.2em;'>AI-Powered CV Analysis for Perfect Job Matches</p>", unsafe_allow_html=True)
            
            tab1, tab2 = st.tabs(["Login", "Register"])
            
            with tab1:
                show_login_page(db_manager, auth_manager)
            
            with tab2:
                show_registration_page(db_manager, auth_manager)

if __name__ == "__main__":
    main()
