import streamlit as st
import sys
import traceback

# Page configuration
st.set_page_config(
    page_title="CareerVertex - AI CV Analysis",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Debug mode - set to False in production
DEBUG = True

try:
    # Import required modules with error handling
    try:
        from core.database import DatabaseManager
        from core.auth import AuthManager
    except ImportError as e:
        st.error(f"Failed to import core modules: {e}")
        st.info("Make sure all files are in the correct directories: core/, pages/, etc.")
        st.stop()
    
    try:
        from pages.registration import show_registration_page
        from pages.login import show_login_page
        from pages.dashboard import show_dashboard
    except ImportError as e:
        st.error(f"Failed to import page modules: {e}")
        st.stop()
    
    try:
        from static.styles import CUSTOM_CSS
        # Apply custom CSS
        st.markdown(f"<style>{CUSTOM_CSS}</style>", unsafe_allow_html=True)
    except ImportError:
        st.warning("Failed to load custom styles")
        # Continue without styles
    
    # Initialize managers
    @st.cache_resource
    def init_managers():
        try:
            db_manager = DatabaseManager()
            auth_manager = AuthManager(db_manager)
            return db_manager, auth_manager
        except Exception as e:
            st.error(f"Failed to initialize managers: {e}")
            if DEBUG:
                st.exception(e)
            return None, None
    
    def main():
        """Main application entry point."""
        
        # Show title immediately
        st.title("CareerVertex")
        
        # Initialize managers
        db_manager, auth_manager = init_managers()
        
        if not db_manager:
            st.error("Database connection failed. Please check your configuration.")
            st.info("""
            Required secrets in .streamlit/secrets.toml:
            - DB_HOST
            - DB_PORT
            - DB_NAME
            - DB_USER
            - DB_PASSWORD
            """)
            return
        
        # Initialize database schema if needed
        if 'db_initialized' not in st.session_state:
            with st.spinner("Initializing database..."):
                if db_manager.initialize_schema():
                    st.session_state.db_initialized = True
                else:
                    st.error("Failed to initialize database schema.")
                    return
        
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
                st.rerun()
        
        # Check for payment success
        if "payment" in query_params:
            if query_params["payment"] == "success" and "session_id" in query_params:
                st.success("Payment received! Check your email for the login link.")
                # Here you would verify the payment with Stripe
                # For now, just show the message
        
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
    
    # Run the main function
    main()

except Exception as e:
    st.error("An unexpected error occurred")
    if DEBUG:
        st.exception(e)
        st.code(traceback.format_exc())
    else:
        st.error("Please refresh the page or contact support if the problem persists.")
