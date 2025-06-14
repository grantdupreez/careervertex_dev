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

def test_database_connection():
    """Test basic database connection."""
    try:
        # First try direct connection like in test files
        import psycopg2
        print("Testing direct psycopg2 connection...")
        
        test_conn = psycopg2.connect(
            dbname=st.secrets["DB_NAME"],
            user=st.secrets["DB_USER"],
            password=st.secrets["DB_PASSWORD"],
            host=st.secrets["DB_HOST"],
            port=st.secrets["DB_PORT"],
            sslmode='require'
        )
        
        # Test query
        cur = test_conn.cursor()
        cur.execute("SELECT 1 as test")
        result = cur.fetchone()
        cur.close()
        test_conn.close()
        
        if result and result[0] == 1:
            print("Direct connection successful!")
            
            # Now test DatabaseManager
            from core.database import DatabaseManager
            db = DatabaseManager()
            
            # Test DatabaseManager query
            result = db.execute("SELECT 1 as test")
            if result and result[0]['test'] == 1:
                return True, db
            else:
                print(f"DatabaseManager query failed: {result}")
                return False, None
        else:
            print("Direct connection query failed")
            return False, None
            
    except Exception as e:
        print(f"Database connection test failed: {e}")
        # Show more detailed error in console
        import traceback
        traceback.print_exc()
        return False, None

def check_and_create_tables(db_manager):
    """Check existing tables and create missing ones."""
    try:
        # Get existing tables
        existing_tables = db_manager.get_existing_tables()
        required_tables = ['users', 'cvs', 'analyses', 'payments']
        
        print(f"Existing tables: {existing_tables}")
        
        # Check what's missing
        missing_tables = [t for t in required_tables if t not in existing_tables]
        
        if not missing_tables:
            print("All required tables exist")
            return True
        
        print(f"Missing tables: {missing_tables}")
        
        # Try to create missing tables
        tables_created, tables_checked = db_manager.create_tables_if_needed()
        
        # Verify all tables now exist
        existing_after = db_manager.get_existing_tables()
        still_missing = [t for t in required_tables if t not in existing_after]
        
        if not still_missing:
            print("All tables created successfully")
            return True
        else:
            print(f"Failed to create tables: {still_missing}")
            return False
            
    except Exception as e:
        print(f"Error checking/creating tables: {e}")
        traceback.print_exc()
        return False

def main():
    """Main application entry point."""
    
    # Load custom styles FIRST
    try:
        from static.styles import CUSTOM_CSS
        st.markdown(f"<style>{CUSTOM_CSS}</style>", unsafe_allow_html=True)
    except ImportError:
        # Continue without custom styles
        pass
    
    # Show title with styling
    st.markdown("""
        <div style='text-align: center; padding: 2rem 0;'>
            <h1 style='font-size: 3rem; margin-bottom: 0.5rem;'>
                <span style='color: #0A1F3D;'>Career</span><span style='color: #B8860B;'>Vertex</span>
            </h1>
            <p style='font-size: 1.2rem; color: #555;'>AI-Powered CV Analysis for Perfect Job Matches</p>
        </div>
    """, unsafe_allow_html=True)
    
    # Step 1: Test database connection
    with st.spinner("Connecting to database..."):
        connected, db_manager = test_database_connection()
    
    if not connected:
        st.error("❌ Database connection failed")
        st.info("""
        **Required Configuration:**
        
        Please ensure these secrets are set in `.streamlit/secrets.toml`:
        ```toml
        DB_HOST = "your-database-host"
        DB_PORT = "5432"
        DB_NAME = "your-database-name"
        DB_USER = "your-username"
        DB_PASSWORD = "your-password"
        ```
        """)
        
        # Show current configuration status
        with st.expander("Configuration Status"):
            required_secrets = ["DB_HOST", "DB_PORT", "DB_NAME", "DB_USER", "DB_PASSWORD"]
            for secret in required_secrets:
                if secret in st.secrets:
                    st.success(f"✅ {secret} is configured")
                else:
                    st.error(f"❌ {secret} is missing")
        return
    
    # Step 2: Check and create tables if needed
    if 'db_ready' not in st.session_state:
        with st.spinner("Checking database tables..."):
            if check_and_create_tables(db_manager):
                st.session_state.db_ready = True
            else:
                st.error("❌ Could not initialize database tables")
                return
    
    # Step 3: Initialize auth manager
    try:
        from core.auth import AuthManager
        auth_manager = AuthManager(db_manager)
    except Exception as e:
        st.error(f"Failed to initialize authentication: {e}")
        return
    
    # Step 4: Load pages and components
    try:
        from pages.registration import show_registration_page
        from pages.login import show_login_page
        from pages.dashboard import show_dashboard
    except ImportError as e:
        st.error(f"Failed to import page modules: {e}")
        st.info("Make sure all files are in the correct directories: core/, pages/, etc.")
        return
    
    # Step 5: Check for payment success callback
    query_params = st.query_params
    if "payment" in query_params:
        if query_params["payment"] == "success" and "session_id" in query_params:
            session_id = query_params["session_id"]
            
            # Process the payment
            from core.payment import verify_payment_and_login
            success, user_data = verify_payment_and_login(db_manager, auth_manager, session_id)
            
            if success and user_data:
                st.session_state.user_id = user_data['user_id']
                st.session_state.user_data = user_data
                st.query_params.clear()
                st.success("✅ Payment successful! Welcome to CareerVertex Pro!")
                st.rerun()
            else:
                st.error("Failed to verify payment. Please contact support.")
                st.query_params.clear()
        elif query_params["payment"] == "cancelled":
            st.warning("Payment was cancelled. You can try again when you're ready.")
            st.query_params.clear()
    
    # Step 6: Route based on authentication
    if 'user_id' in st.session_state:
        # User is logged in - show dashboard
        show_dashboard(db_manager, auth_manager)
    else:
        # User not logged in - show login/registration with proper styling
        st.markdown("---")
        
        # Create centered layout with styled background
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
            # Login/Register tabs with custom styling
            tab1, tab2 = st.tabs(["🔑 Login", "📝 Register"])
            
            with tab1:
                show_login_page(db_manager, auth_manager)
            
            with tab2:
                show_registration_page(db_manager, auth_manager)
        
        # Features section with index.html styling
        st.markdown("---")
        st.markdown("""
            <div style='background-color: white; padding: 3rem 0; margin: 0 -5rem;'>
                <div style='max-width: 1200px; margin: 0 auto; padding: 0 2rem;'>
                    <h2 style='text-align: center; color: #0A1F3D; font-size: 2.5rem; margin-bottom: 3rem;'>
                        Core Features
                    </h2>
                    <div style='display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 2rem;'>
        """, unsafe_allow_html=True)
        
        features = [
            {
                "icon": "🎯",
                "title": "AI Keyword Analysis",
                "description": "Our proprietary algorithm identifies critical keywords from job descriptions that match your experience."
            },
            {
                "icon": "📊",
                "title": "Match Score Analytics",
                "description": "Receive a detailed match score showing how well your CV aligns with specific job requirements."
            },
            {
                "icon": "💼",
                "title": "Industry Insights",
                "description": "Leverage industry-specific data to understand what skills are most valued in your target roles."
            }
        ]
        
        cols = st.columns(3)
        for idx, feature in enumerate(features):
            with cols[idx]:
                st.markdown(f"""
                    <div style='background: #F8F9FA; border-radius: 5px; padding: 2rem; 
                                box-shadow: 0 10px 30px rgba(0,0,0,0.03); border: 1px solid #E1E5EA;
                                transition: all 0.3s ease; height: 100%;'>
                        <div style='font-size: 3rem; text-align: center; margin-bottom: 1rem;'>{feature['icon']}</div>
                        <h3 style='color: #0A1F3D; text-align: center; margin-bottom: 1rem;'>{feature['title']}</h3>
                        <p style='color: #555; text-align: center;'>{feature['description']}</p>
                    </div>
                """, unsafe_allow_html=True)
        
        st.markdown("</div></div></div>", unsafe_allow_html=True)
        
        # Pricing section
        st.markdown("---")
        st.markdown("""
            <div style='background: linear-gradient(135deg, #F0F2F5 0%, #F8F9FA 100%); 
                        padding: 3rem 0; margin: 0 -5rem; text-align: center;'>
                <div style='max-width: 500px; margin: 0 auto;'>
                    <h2 style='color: #0A1F3D; font-size: 2.5rem; margin-bottom: 2rem;'>Simple Pricing</h2>
                    <div style='background: white; border-radius: 8px; padding: 3rem; 
                                box-shadow: 0 15px 40px rgba(0,0,0,0.05); border: 1px solid #E1E5EA;'>
                        <div style='background: linear-gradient(135deg, #B8860B 0%, #D4AF37 100%); 
                                    color: white; padding: 0.5rem 1rem; border-radius: 20px; 
                                    display: inline-block; margin-bottom: 1rem; font-weight: 600;'>
                            MONTHLY SUBSCRIPTION
                        </div>
                        <div style='font-size: 3rem; color: #0A1F3D; font-weight: 700; margin-bottom: 1rem;'>
                            £25<span style='font-size: 1.2rem; font-weight: 400;'>/month</span>
                        </div>
                        <ul style='list-style: none; padding: 0; text-align: left; margin: 2rem 0;'>
                            <li style='padding: 0.5rem 0; color: #555;'>✅ Unlimited CV analyses</li>
                            <li style='padding: 0.5rem 0; color: #555;'>✅ Keyword optimisation suggestions</li>
                            <li style='padding: 0.5rem 0; color: #555;'>✅ ATS compatibility check</li>
                            <li style='padding: 0.5rem 0; color: #555;'>✅ Match score analytics</li>
                            <li style='padding: 0.5rem 0; color: #555;'>✅ Industry-specific insights</li>
                            <li style='padding: 0.5rem 0; color: #555;'>✅ CV version management</li>
                        </ul>
                    </div>
                </div>
            </div>
        """, unsafe_allow_html=True)

# Error handling wrapper
try:
    if __name__ == "__main__":
        main()
except Exception as e:
    st.error("❌ An unexpected error occurred")
    if DEBUG:
        st.exception(e)
        st.code(traceback.format_exc())
    else:
        st.error("Please refresh the page or contact support if the problem persists.")
