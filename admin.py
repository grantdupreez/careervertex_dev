import streamlit as st
import psycopg2
from psycopg2 import pool
from datetime import datetime, timedelta
import pandas as pd
import bcrypt
from contextlib import contextmanager
import time

st.set_page_config(page_title="CareerVertex Admin", page_icon="🔧", layout="wide")

# Initialize connection pool
@st.cache_resource
def init_connection_pool():
    """Initialize a connection pool for the database"""
    try:
        return psycopg2.pool.SimpleConnectionPool(
            1, 20,  # min and max connections
            dbname=st.secrets["DB_NAME"],
            user=st.secrets["DB_USER"],
            password=st.secrets["DB_PASSWORD"],
            host=st.secrets["DB_HOST"],
            port=st.secrets["DB_PORT"],
            sslmode='require'
        )
    except Exception as e:
        st.error(f"Failed to create connection pool: {e}")
        return None

# Context manager for database connections
@contextmanager
def get_db_connection():
    """Get a database connection from the pool"""
    pool = init_connection_pool()
    if not pool:
        raise Exception("Connection pool not initialized")
    
    conn = None
    try:
        conn = pool.getconn()
        yield conn
        conn.commit()
    except Exception as e:
        if conn:
            conn.rollback()
        raise e
    finally:
        if conn:
            pool.putconn(conn)

# Helper function to execute queries
def execute_query(query, params=None, fetch=False):
    """Execute a database query with proper error handling"""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, params)
                if fetch:
                    return cur.fetchall()
                return cur.rowcount
    except Exception as e:
        st.error(f"Database error: {e}")
        return None

# Helper function to get single value
def get_single_value(query, params=None):
    """Get a single value from the database"""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, params)
                result = cur.fetchone()
                return result[0] if result else None
    except Exception as e:
        st.error(f"Database error: {e}")
        return None

# Admin authentication
ADMIN_EMAILS = st.secrets.get("ADMIN_EMAILS", "admin@careervertex.com").split(",")
ADMIN_PASSWORD = st.secrets.get("ADMIN_PASSWORD", "admin123")

if 'admin_authenticated' not in st.session_state:
    st.session_state.admin_authenticated = False

if not st.session_state.admin_authenticated:
    st.title("🔒 Admin Login")
    
    with st.form("admin_login"):
        email = st.text_input("Admin Email")
        password = st.text_input("Password", type="password")
        
        if st.form_submit_button("Login"):
            if email in ADMIN_EMAILS and password == ADMIN_PASSWORD:
                st.session_state.admin_authenticated = True
                st.rerun()
            else:
                st.error("Invalid credentials")
else:
    st.title("🔧 CareerVertex Admin Panel")
    
    # Logout button
    if st.button("🚪 Logout"):
        st.session_state.admin_authenticated = False
        st.rerun()
    
    # Navigation tabs
    tab1, tab2, tab3, tab4 = st.tabs(["📊 Dashboard", "👥 Users", "💳 Subscriptions", "🔧 Tools"])
    
    with tab1:
        st.header("Dashboard")
        
        # Test connection button
        if st.button("Test Database Connection"):
            try:
                with get_db_connection() as conn:
                    with conn.cursor() as cur:
                        cur.execute("SELECT 1")
                        st.success("✅ Database connection successful!")
            except Exception as e:
                st.error(f"❌ Connection failed: {e}")
        
        # Simple stats
        st.subheader("Quick Stats")
        if st.button("Load Stats"):
            col1, col2, col3 = st.columns(3)
            
            # Total users
            user_count = get_single_value("SELECT COUNT(*) FROM users")
            with col1:
                st.metric("Total Users", user_count if user_count is not None else "Error")
            
            # Active subs
            active_count = get_single_value("SELECT COUNT(*) FROM users WHERE subscription_status = 'active'")
            with col2:
                st.metric("Active Subs", active_count if active_count is not None else "Error")
            
            # Total CVs
            cv_count = get_single_value("SELECT COUNT(*) FROM cvs")
            with col3:
                st.metric("Total CVs", cv_count if cv_count is not None else "Error")
    
    with tab2:
        st.header("User Management")
        
        # Search form
        with st.form("user_search"):
            email_search = st.text_input("Search by email")
            submitted = st.form_submit_button("Search")
            
            if submitted:
                if email_search:
                    query = "SELECT user_id, email, full_name, subscription_status FROM users WHERE email ILIKE %s LIMIT 10"
                    params = (f"%{email_search}%",)
                else:
                    query = "SELECT user_id, email, full_name, subscription_status FROM users ORDER BY created_at DESC LIMIT 10"
                    params = None
                
                users = execute_query(query, params, fetch=True)
                
                if users:
                    for user in users:
                        st.write(f"**{user[1]}** - {user[2] or 'No name'} - Status: {user[3] or 'Inactive'}")
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            if st.button(f"Activate Sub", key=f"act_{user[0]}"):
                                result = execute_query(
                                    "UPDATE users SET subscription_status = 'active', subscription_end = %s WHERE user_id = %s",
                                    (datetime.now() + timedelta(days=30), user[0])
                                )
                                if result is not None:
                                    st.success("Activated!")
                                    time.sleep(1)
                                    st.rerun()
                        
                        with col2:
                            if st.button(f"Reset Password", key=f"pwd_{user[0]}"):
                                new_pwd = "password123"
                                pwd_hash = bcrypt.hashpw(new_pwd.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                                result = execute_query(
                                    "UPDATE users SET password_hash = %s WHERE user_id = %s",
                                    (pwd_hash, user[0])
                                )
                                if result is not None:
                                    st.success(f"Password reset to: {new_pwd}")
                        
                        st.divider()
                else:
                    st.info("No users found")
    
    with tab3:
        st.header("Subscription Management")
        
        if st.button("Show Active Subscriptions"):
            try:
                with get_db_connection() as conn:
                    query = """
                        SELECT email, subscription_end 
                        FROM users 
                        WHERE subscription_status = 'active' 
                        ORDER BY subscription_end DESC
                        LIMIT 20
                    """
                    df = pd.read_sql(query, conn)
                    
                    if not df.empty:
                        # Format the date column
                        df['subscription_end'] = pd.to_datetime(df['subscription_end']).dt.strftime('%Y-%m-%d %H:%M')
                        st.dataframe(df, use_container_width=True)
                    else:
                        st.info("No active subscriptions")
                        
            except Exception as e:
                st.error(f"Failed to load: {e}")
        
        if st.button("Update Expired Subscriptions"):
            count = execute_query(
                "UPDATE users SET subscription_status = 'expired' WHERE subscription_status = 'active' AND subscription_end < NOW()"
            )
            if count is not None:
                st.success(f"Updated {count} expired subscriptions")
        
        # Add subscription statistics
        st.subheader("Subscription Statistics")
        if st.button("Load Subscription Stats"):
            try:
                with get_db_connection() as conn:
                    query = """
                        SELECT 
                            subscription_status,
                            COUNT(*) as count
                        FROM users
                        GROUP BY subscription_status
                        ORDER BY count DESC
                    """
                    df = pd.read_sql(query, conn)
                    
                    if not df.empty:
                        st.dataframe(df, use_container_width=True)
                        
                        # Show a bar chart
                        st.bar_chart(df.set_index('subscription_status')['count'])
                    else:
                        st.info("No subscription data available")
                        
            except Exception as e:
                st.error(f"Failed to load stats: {e}")
    
    with tab4:
        st.header("Database Tools")
        
        # Table info
        st.subheader("Database Tables")
        if st.button("Show Tables"):
            query = """
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                ORDER BY table_name
            """
            tables = execute_query(query, fetch=True)
            if tables:
                for table in tables:
                    st.write(f"📊 {table[0]}")
        
        # Simple query runner
        st.subheader("Run Query")
        st.warning("⚠️ Only SELECT queries are allowed for safety")
        
        query = st.text_area("SQL Query (SELECT only)", height=150)
        
        if st.button("Execute Query"):
            if query.strip().upper().startswith("SELECT"):
                try:
                    with get_db_connection() as conn:
                        df = pd.read_sql(query, conn)
                        st.success(f"Query returned {len(df)} rows")
                        st.dataframe(df, use_container_width=True)
                except Exception as e:
                    st.error(f"Query failed: {e}")
            else:
                st.error("Only SELECT queries are allowed for safety reasons")
        
        # Database health check
        st.subheader("Database Health Check")
        if st.button("Run Health Check"):
            col1, col2 = st.columns(2)
            
            with col1:
                # Check connection pool status
                pool = init_connection_pool()
                if pool:
                    st.metric("Connection Pool", "Active")
                    st.metric("Pool Size", f"{pool.minconn}-{pool.maxconn}")
                else:
                    st.metric("Connection Pool", "Error")
            
            with col2:
                # Check database size
                db_size = get_single_value(
                    "SELECT pg_size_pretty(pg_database_size(current_database()))"
                )
                st.metric("Database Size", db_size if db_size else "Unknown")
                
                # Check active connections
                active_conns = get_single_value(
                    "SELECT count(*) FROM pg_stat_activity"
                )
                st.metric("Active Connections", active_conns if active_conns else "Unknown")
