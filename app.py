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
        from core.database import DatabaseManager
        db = DatabaseManager()
        
        # Test basic connection
        result = db.execute("SELECT 1 as test")
        if result and result[0]['test'] == 1:
            return True, db
        return False, None
    except Exception as e:
        print(f"Database connection test failed: {e}")
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
    
    # Show title
    st.title("🎯 CareerVertex")
    st.markdown("*AI-Powered CV Analysis for Perfect Job Matches*")
    
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
                
                # Show manual creation option
                st.warning("""
                **Manual Setup Required**
                
                Your database user may not have CREATE permissions.
                Please run the SQL schema manually in your database.
                """)
                
                with st.expander("📋 SQL Schema"):
                    st.code("""
-- Create tables
CREATE TABLE IF NOT EXISTS users (
    user_id UUID PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(255),
    subscription_status VARCHAR(50) DEFAULT 'inactive',
    subscription_start TIMESTAMP,
    subscription_end TIMESTAMP,
    stripe_customer_id VARCHAR(255),
    stripe_subscription_id VARCHAR(255),
    created_at TIMESTAMP DEFAULT NOW(),
    last_login TIMESTAMP,
    login_token VARCHAR(255),
    token_expires TIMESTAMP
);

CREATE TABLE IF NOT EXISTS cvs (
    cv_id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(user_id) ON DELETE CASCADE,
    cv_name VARCHAR(255) NOT NULL,
    cv_text TEXT,
    parsed_data JSONB,
    uploaded_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS analyses (
    analysis_id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(user_id) ON DELETE CASCADE,
    cv_id UUID REFERENCES cvs(cv_id) ON DELETE CASCADE,
    job_title VARCHAR(255),
    company VARCHAR(255),
    job_description TEXT,
    parsed_job JSONB,
    analysis_result JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS payments (
    payment_id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(user_id) ON DELETE CASCADE,
    stripe_session_id VARCHAR(255),
    amount DECIMAL(10, 2),
    status VARCHAR(50),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_token ON users(login_token);
CREATE INDEX IF NOT EXISTS idx_analyses_user ON analyses(user_id);
CREATE INDEX IF NOT EXISTS idx_cvs_user ON cvs(user_id);
                    """, language="sql")
                
                if st.button("🔄 Retry After Manual Setup"):
                    del st.session_state['db_ready']
                    st.rerun()
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
    
    # Step 5: Load styles (optional)
    try:
        from static.styles import CUSTOM_CSS
        st.markdown(f"<style>{CUSTOM_CSS}</style>", unsafe_allow_html=True)
    except ImportError:
        # Continue without custom styles
        pass
    
    # Step 6: Check for login token in URL
    query_params = st.query_params
    if "token" in query_params:
        token = query_params["token"]
        user_data = auth_manager.verify_login_token(token)
        if user_data:
            st.session_state.user_id = user_data['user_id']
            st.session_state.user_data = user_data
            st.query_params.clear()
            st.success("✅ Login successful!")
            st.rerun()
    
    # Step 7: Check for payment success
    if "payment" in query_params:
        if query_params["payment"] == "success" and "session_id" in query_params:
            st.success("✅ Payment received! Check your email for the login link.")
            st.query_params.clear()
    
    # Step 8: Route based on authentication
    if 'user_id' in st.session_state:
        # User is logged in - show dashboard
        show_dashboard(db_manager, auth_manager)
    else:
        # User not logged in - show login/registration
        st.markdown("---")
        
        # Create centered layout
        col1, col2, col3 = st.columns([1, 2, 1])
        
        with col2:
            # Welcome section
            st.markdown("""
            <div style='text-align: center; padding: 2rem 0;'>
                <h2>Welcome to CareerVertex</h2>
                <p style='font-size: 1.1em; color: #666;'>
                    Upload your CV and get instant AI-powered analysis to match any job description.
                    Improve your chances with tailored suggestions and cover letters.
                </p>
            </div>
            """, unsafe_allow_html=True)
            
            # Login/Register tabs
            tab1, tab2 = st.tabs(["🔑 Login", "📝 Register"])
            
            with tab1:
                show_login_page(db_manager, auth_manager)
            
            with tab2:
                show_registration_page(db_manager, auth_manager)
        
        # Footer info
        st.markdown("---")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("""
            **✨ Features**
            - AI-powered CV analysis
            - Job match scoring
            - Keyword optimization
            - Cover letter generation
            """)
        
        with col2:
            st.markdown("""
            **💎 Benefits**
            - Unlimited analyses
            - Multiple CV storage
            - Interview tips
            - Regular updates
            """)
        
        with col3:
            st.markdown("""
            **💰 Pricing**
            - £25/month
            - Cancel anytime
            - Secure payments
            - Instant access
            """)

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
        
    # Show basic diagnostic info
    with st.expander("Diagnostic Information"):
        st.write("Python version:", sys.version)
        st.write("Streamlit version:", st.__version__)
        
        # Check module availability
        modules = ['psycopg2', 'bcrypt', 'anthropic', 'stripe', 'PyPDF2', 'docx']
        st.write("\n**Module Status:**")
        for module in modules:
            try:
                __import__(module)
                st.write(f"✅ {module}")
            except ImportError:
                st.write(f"❌ {module}")
