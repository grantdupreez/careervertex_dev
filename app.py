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

# Debug mode
DEBUG = True

def main():
    """Main application entry point."""
    
    # Load custom styles
    try:
        from static.styles import CUSTOM_CSS
        st.markdown(f"<style>{CUSTOM_CSS}</style>", unsafe_allow_html=True)
    except:
        pass
    
    # Show title
    st.markdown("""
        <div style='text-align: center; padding: 2rem 0;'>
            <h1 style='font-size: 3rem; margin-bottom: 0.5rem;'>
                <span style='color: #0A1F3D;'>Career</span><span style='color: #B8860B;'>Vertex</span>
            </h1>
            <p style='font-size: 1.2rem; color: #555;'>AI-Powered CV Analysis for Perfect Job Matches</p>
        </div>
    """, unsafe_allow_html=True)
    
    # Initialize core components
    db_manager = None
    auth_manager = None
    
    # Try to initialize database
    try:
        from core.database import DatabaseManager
        db_manager = DatabaseManager()
        st.success("✅ Database connected")
    except Exception as e:
        st.error(f"⚠️ Database initialization failed: {str(e)}")
        if DEBUG:
            st.code(traceback.format_exc())
    
    # Try to initialize auth
    if db_manager:
        try:
            from core.auth import AuthManager
            auth_manager = AuthManager(db_manager)
            st.success("✅ Authentication initialized")
        except Exception as e:
            st.error(f"⚠️ Authentication initialization failed: {str(e)}")
            if DEBUG:
                st.code(traceback.format_exc())
    
    # Check if we can load pages
    pages_loaded = False
    try:
        from pages.registration import show_registration_page
        from pages.login import show_login_page
        from pages.dashboard import show_dashboard
        pages_loaded = True
        st.success("✅ Page modules loaded")
    except ImportError as e:
        st.error(f"⚠️ Failed to import page modules: {e}")
        if DEBUG:
            st.code(traceback.format_exc())
    
    st.markdown("---")
    
    # Main application logic
    if not db_manager or not auth_manager or not pages_loaded:
        st.warning("Running in limited mode due to initialization issues")
        
        # Show basic login/register forms
        tab1, tab2 = st.tabs(["Login", "Register"])
        
        with tab1:
            st.markdown("### Login")
            email = st.text_input("Email", key="login_email")
            password = st.text_input("Password", type="password", key="login_password")
            if st.button("Login", disabled=True):
                st.error("Login disabled - database not connected")
        
        with tab2:
            st.markdown("### Register")
            st.info("Registration is currently unavailable due to database connection issues")
    
    else:
        # Normal operation - everything is working
        
        # Check for payment callback
        query_params = st.query_params
        if "payment" in query_params:
            if query_params["payment"] == "success" and "session_id" in query_params:
                try:
                    from core.payment import verify_payment_and_login
                    success, user_data = verify_payment_and_login(db_manager, auth_manager, query_params["session_id"])
                    
                    if success and user_data:
                        st.session_state.user_id = user_data['user_id']
                        st.session_state.user_data = user_data
                        st.query_params.clear()
                        st.success("✅ Payment successful! Welcome to CareerVertex Pro!")
                        st.rerun()
                except Exception as e:
                    st.error(f"Payment verification failed: {e}")
                    st.query_params.clear()
        
        # Route based on authentication
        if 'user_id' in st.session_state:
            # User is logged in - show dashboard
            show_dashboard(db_manager, auth_manager)
        else:
            # Show login/registration
            st.markdown("""
                <div style='background: linear-gradient(135deg, #F8F9FA 0%, #E1E5EA 100%); 
                            padding: 3rem 0; margin: -1rem -5rem 2rem -5rem;'>
                    <div style='max-width: 800px; margin: 0 auto; text-align: center;'>
                        <h2 style='color: #0A1F3D; font-size: 2.5rem; margin-bottom: 1rem;'>
                            Perfect CV-Job <span style='background: linear-gradient(135deg, #B8860B 0%, #D4AF37 100%);
                            -webkit-background-clip: text; -webkit-text-fill-color: transparent;'>Match Every Time</span>
                        </h2>
                        <p style='font-size: 1.1em; color: #555; max-width: 600px; margin: 0 auto;'>
                            CareerVertex's AI-powered CV matching tool analyses your CV against job descriptions 
                            to ensure you position yourself as the perfect candidate.
                        </p>
                    </div>
                </div>
            """, unsafe_allow_html=True)
            
            col1, col2, col3 = st.columns([1, 2, 1])
            
            with col2:
                tab1, tab2 = st.tabs(["🔑 Login", "📝 Register"])
                
                with tab1:
                    show_login_page(db_manager, auth_manager)
                
                with tab2:
                    show_registration_page(db_manager, auth_manager)
            
            # Features section
            st.markdown("---")
            
            cols = st.columns(3)
            features = [
                {
                    "icon": "🎯",
                    "title": "AI Keyword Analysis",
                    "description": "Our algorithm identifies critical keywords from job descriptions."
                },
                {
                    "icon": "📊",
                    "title": "Match Score Analytics",
                    "description": "Get detailed match scores with improvement recommendations."
                },
                {
                    "icon": "💼",
                    "title": "Industry Insights",
                    "description": "Leverage industry data to understand valued skills."
                }
            ]
            
            for idx, feature in enumerate(features):
                with cols[idx]:
                    st.markdown(f"""
                        <div style='text-align: center; padding: 2rem; background: #F8F9FA; 
                                    border-radius: 8px; height: 100%;'>
                            <div style='font-size: 3rem; margin-bottom: 1rem;'>{feature['icon']}</div>
                            <h3 style='color: #0A1F3D; margin-bottom: 1rem;'>{feature['title']}</h3>
                            <p style='color: #666;'>{feature['description']}</p>
                        </div>
                    """, unsafe_allow_html=True)

# Run the app
if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        st.error("❌ An unexpected error occurred")
        if DEBUG:
            st.exception(e)
        else:
            st.error("Please refresh the page or contact support if the problem persists.")
