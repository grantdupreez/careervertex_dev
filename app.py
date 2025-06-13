import streamlit as st
import sys
import os

# Add current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Page configuration
st.set_page_config(
    page_title="CareerVertex - AI CV Analysis",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Import and apply styles
try:
    from static.styles import CUSTOM_CSS
    st.markdown(f"<style>{CUSTOM_CSS}</style>", unsafe_allow_html=True)
except:
    pass

# Import required modules
from core.database import DatabaseManager
from core.auth import AuthManager
from pages.registration import show_registration_page
from pages.login import show_login_page
from pages.dashboard import show_dashboard

def main():
    """Main application."""
    st.title("CareerVertex")
    
    # Initialize database manager
    db_manager = DatabaseManager()
    
    # Check if we can connect
    if not db_manager.connection_params:
        st.error("Database configuration missing!")
        return
    
    # Quick connection test
    test = db_manager.execute("SELECT 1")
    if test is None:
        st.error("Cannot connect to database. Please check your configuration.")
        return
    
    # Check if tables exist
    tables = db_manager.execute("""
        SELECT tablename FROM pg_tables 
        WHERE schemaname = 'public' 
        AND tablename IN ('users', 'cvs', 'analyses', 'payments')
    """)
    
    if not tables or len(tables) < 4:
        st.warning("Some database tables are missing. Attempting to create them...")
        
        # Try to create tables
        if not db_manager.initialize_schema():
            st.error("""
            Failed to create database tables. Please run the following SQL manually in your database:
            
            1. Go to your database admin panel
            2. Run the SQL from create_schema.sql
            3. Refresh this page
            """)
            return
    
    # Tables exist, proceed with app
    st.session_state.db_initialized = True
    
    # Initialize auth manager
    auth_manager = AuthManager(db_manager)
    
    # Check for login token in URL
    query_params = st.query_params
    if "token" in query_params:
        token = query_params["token"]
        user_data = auth_manager.verify_login_token(token)
        if user_data:
            st.session_state.user_id = user_data['user_id']
            st.session_state.user_data = user_data
            st.query_params.clear()
            st.success("Login successful!")
            st.rerun()
    
    # Check for payment return
    if "payment" in query_params:
        if query_params["payment"] == "success":
            st.success("Payment successful! Check your email for login instructions.")
            st.query_params.clear()
        elif query_params["payment"] == "cancelled":
            st.warning("Payment was cancelled.")
            st.query_params.clear()
    
    # Show appropriate page
    if 'user_id' in st.session_state:
        show_dashboard(db_manager, auth_manager)
    else:
        # Login/Register page
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.markdown("<h2 style='text-align: center;'>AI-Powered CV Analysis</h2>", unsafe_allow_html=True)
            
            tab1, tab2 = st.tabs(["Login", "Register"])
            
            with tab1:
                show_login_page(db_manager, auth_manager)
            
            with tab2:
                show_registration_page(db_manager, auth_manager)

if __name__ == "__main__":
    main()
