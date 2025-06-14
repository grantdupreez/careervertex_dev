import streamlit as st
import psycopg2
from psycopg2 import pool
from psycopg2.extras import DictCursor, Json
from datetime import datetime, timedelta
import pandas as pd
import bcrypt
from contextlib import contextmanager
import time
import stripe
import uuid
import socket
import requests
import traceback
import json
import re

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
            with conn.cursor(cursor_factory=DictCursor) as cur:
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
    if st.button("🚪 Logout", key="logout"):
        st.session_state.admin_authenticated = False
        st.rerun()
    
    # Navigation tabs
    tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs([
        "📊 Dashboard", 
        "👥 Users", 
        "💳 Subscriptions", 
        "💰 Payments",
        "🔧 Database Tools",
        "🔌 Connection Debug",
        "💳 Stripe Debug",
        "📧 Email Tools"
    ])
    
    with tab1:
        st.header("Dashboard")
        
        # Connection status
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("🔌 System Status")
            
            # Test database connection
            try:
                with get_db_connection() as conn:
                    with conn.cursor() as cur:
                        cur.execute("SELECT version()")
                        version = cur.fetchone()
                        st.success("✅ Database: Connected")
                        with st.expander("PostgreSQL Version"):
                            st.code(version[0])
            except Exception as e:
                st.error(f"❌ Database: {str(e)}")
        
        with col2:
            st.subheader("🔑 API Status")
            
            # Check Stripe
            if "STRIPE_SECRET_KEY" in st.secrets:
                try:
                    stripe.api_key = st.secrets["STRIPE_SECRET_KEY"]
                    account = stripe.Account.retrieve()
                    st.success("✅ Stripe: Connected")
                    mode = "TEST" if "sk_test_" in st.secrets["STRIPE_SECRET_KEY"] else "LIVE"
                    st.info(f"Mode: {mode}")
                except Exception as e:
                    st.error("❌ Stripe: Failed")
            else:
                st.warning("⚠️ Stripe: Not configured")
            
            # Check Anthropic
            if "ANTHROPIC_API_KEY" in st.secrets:
                st.success("✅ Anthropic: Configured")
            else:
                st.warning("⚠️ Anthropic: Not configured")
        
        # Statistics
        st.subheader("📈 Quick Stats")
        
        col1, col2, col3, col4 = st.columns(4)
        
        # Total users
        user_count = get_single_value("SELECT COUNT(*) FROM users")
        with col1:
            st.metric("Total Users", user_count if user_count is not None else "Error")
        
        # Active subscriptions
        active_count = get_single_value("SELECT COUNT(*) FROM users WHERE subscription_status = 'active'")
        with col2:
            st.metric("Active Subs", active_count if active_count is not None else "Error")
        
        # Total CVs
        cv_count = get_single_value("SELECT COUNT(*) FROM cvs")
        with col3:
            st.metric("Total CVs", cv_count if cv_count is not None else "Error")
        
        # Total analyses
        analysis_count = get_single_value("SELECT COUNT(*) FROM analyses")
        with col4:
            st.metric("Total Analyses", analysis_count if analysis_count is not None else "Error")
        
        # Recent activity
        st.subheader("🕐 Recent Activity")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**Recent Registrations**")
            recent_users = execute_query("""
                SELECT email, full_name, created_at 
                FROM users 
                ORDER BY created_at DESC 
                LIMIT 5
            """, fetch=True)
            
            if recent_users:
                for user in recent_users:
                    st.write(f"• {user['email']} - {user['created_at'].strftime('%Y-%m-%d %H:%M')}")
            else:
                st.info("No recent registrations")
        
        with col2:
            st.write("**Recent Analyses**")
            recent_analyses = execute_query("""
                SELECT u.email, a.job_title, a.created_at 
                FROM analyses a
                JOIN users u ON a.user_id = u.user_id
                ORDER BY a.created_at DESC 
                LIMIT 5
            """, fetch=True)
            
            if recent_analyses:
                for analysis in recent_analyses:
                    st.write(f"• {analysis['email']} - {analysis['job_title']} - {analysis['created_at'].strftime('%Y-%m-%d %H:%M')}")
            else:
                st.info("No recent analyses")
    
    with tab2:
        st.header("User Management")
        
        # Search and filter
        col1, col2, col3 = st.columns([2, 1, 1])
        
        with col1:
            search_term = st.text_input("Search users (email, name)", placeholder="john@example.com")
        
        with col2:
            status_filter = st.selectbox("Status", ["All", "Active", "Inactive", "Expired"])
        
        with col3:
            sort_by = st.selectbox("Sort by", ["Created (Newest)", "Created (Oldest)", "Last Login"])
        
        # Build query
        query = "SELECT * FROM users WHERE 1=1"
        params = []
        
        if search_term:
            query += " AND (email ILIKE %s OR full_name ILIKE %s)"
            params.extend([f"%{search_term}%", f"%{search_term}%"])
        
        if status_filter != "All":
            if status_filter == "Active":
                query += " AND subscription_status = 'active' AND subscription_end > NOW()"
            elif status_filter == "Inactive":
                query += " AND (subscription_status = 'inactive' OR subscription_status IS NULL)"
            elif status_filter == "Expired":
                query += " AND subscription_status = 'active' AND subscription_end < NOW()"
        
        if sort_by == "Created (Newest)":
            query += " ORDER BY created_at DESC"
        elif sort_by == "Created (Oldest)":
            query += " ORDER BY created_at ASC"
        else:
            query += " ORDER BY last_login DESC NULLS LAST"
        
        query += " LIMIT 20"
        
        # Execute search
        if st.button("🔍 Search", type="primary"):
            users = execute_query(query, params if params else None, fetch=True)
            
            if users:
                st.write(f"Found {len(users)} users")
                
                for user in users:
                    with st.expander(f"👤 {user['email']} - {user['full_name'] or 'No name'}"):
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.write(f"**User ID:** `{user['user_id']}`")
                            st.write(f"**Created:** {user['created_at'].strftime('%Y-%m-%d %H:%M')}")
                            if user['last_login']:
                                st.write(f"**Last Login:** {user['last_login'].strftime('%Y-%m-%d %H:%M')}")
                            else:
                                st.write("**Last Login:** Never")
                        
                        with col2:
                            st.write(f"**Status:** {user['subscription_status'] or 'Inactive'}")
                            if user['subscription_end']:
                                st.write(f"**Sub Ends:** {user['subscription_end'].strftime('%Y-%m-%d')}")
                                if user['subscription_end'] < datetime.now():
                                    st.error("Subscription expired!")
                            if user['stripe_customer_id']:
                                st.write(f"**Stripe ID:** `{user['stripe_customer_id']}`")
                        
                        st.markdown("---")
                        
                        # Action buttons
                        col1, col2, col3, col4 = st.columns(4)
                        
                        with col1:
                            if st.button("🔓 Reset Password", key=f"pwd_{user['user_id']}"):
                                new_pwd = f"reset_{uuid.uuid4().hex[:8]}"
                                pwd_hash = bcrypt.hashpw(new_pwd.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                                
                                result = execute_query(
                                    "UPDATE users SET password_hash = %s WHERE user_id = %s",
                                    (pwd_hash, user['user_id'])
                                )
                                
                                if result is not None:
                                    st.success(f"New password: `{new_pwd}`")
                                    st.info("Copy this password and send to user")
                        
                        with col2:
                            if st.button("💳 Activate Sub", key=f"act_{user['user_id']}"):
                                result = execute_query(
                                    """UPDATE users 
                                    SET subscription_status = 'active', 
                                        subscription_end = %s,
                                        subscription_start = COALESCE(subscription_start, NOW())
                                    WHERE user_id = %s""",
                                    (datetime.now() + timedelta(days=30), user['user_id'])
                                )
                                
                                if result is not None:
                                    st.success("Subscription activated for 30 days!")
                                    time.sleep(1)
                                    st.rerun()
                        
                        with col3:
                            if st.button("📊 View Stats", key=f"stats_{user['user_id']}"):
                                # Get user statistics
                                cv_count = get_single_value(
                                    "SELECT COUNT(*) FROM cvs WHERE user_id = %s",
                                    (user['user_id'],)
                                )
                                
                                analysis_count = get_single_value(
                                    "SELECT COUNT(*) FROM analyses WHERE user_id = %s",
                                    (user['user_id'],)
                                )
                                
                                st.info(f"CVs: {cv_count or 0} | Analyses: {analysis_count or 0}")
                        
                        with col4:
                            if st.button("🗑️ Delete User", key=f"del_{user['user_id']}"):
                                st.session_state[f"confirm_delete_{user['user_id']}"] = True
                        
                        # Confirmation for delete
                        if st.session_state.get(f"confirm_delete_{user['user_id']}", False):
                            st.warning("⚠️ This will permanently delete the user and all their data!")
                            
                            col1, col2 = st.columns(2)
                            with col1:
                                if st.button("✅ Confirm Delete", key=f"confirm_{user['user_id']}", type="primary"):
                                    # Delete all user data
                                    execute_query("DELETE FROM payments WHERE user_id = %s", (user['user_id'],))
                                    execute_query("DELETE FROM analyses WHERE user_id = %s", (user['user_id'],))
                                    execute_query("DELETE FROM cvs WHERE user_id = %s", (user['user_id'],))
                                    execute_query("DELETE FROM users WHERE user_id = %s", (user['user_id'],))
                                    
                                    st.success("User deleted successfully")
                                    del st.session_state[f"confirm_delete_{user['user_id']}"]
                                    time.sleep(1)
                                    st.rerun()
                            
                            with col2:
                                if st.button("❌ Cancel", key=f"cancel_{user['user_id']}"):
                                    del st.session_state[f"confirm_delete_{user['user_id']}"]
                                    st.rerun()
            else:
                st.info("No users found")
        
        # Quick user creation
        st.markdown("---")
        st.subheader("➕ Create Test User")
        
        with st.form("create_user"):
            col1, col2 = st.columns(2)
            
            with col1:
                new_email = st.text_input("Email", value=f"test_{uuid.uuid4().hex[:8]}@example.com")
                new_name = st.text_input("Full Name", value="Test User")
            
            with col2:
                new_password = st.text_input("Password", value="testpass123")
                activate_sub = st.checkbox("Activate subscription", value=True)
            
            if st.form_submit_button("Create User", type="primary"):
                # Check if user exists
                existing = get_single_value(
                    "SELECT user_id FROM users WHERE email = %s",
                    (new_email.lower(),)
                )
                
                if existing:
                    st.error("User already exists!")
                else:
                    # Create user
                    user_id = str(uuid.uuid4())
                    pwd_hash = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                    
                    # Set subscription data if activated
                    sub_status = 'active' if activate_sub else 'inactive'
                    sub_end = datetime.now() + timedelta(days=30) if activate_sub else None
                    sub_start = datetime.now() if activate_sub else None
                    
                    result = execute_query(
                        """INSERT INTO users 
                        (user_id, email, password_hash, full_name, created_at, 
                         subscription_status, subscription_start, subscription_end)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
                        (user_id, new_email.lower(), pwd_hash, new_name, datetime.now(),
                         sub_status, sub_start, sub_end)
                    )
                    
                    if result is not None:
                        st.success(f"✅ User created successfully!")
                        st.info(f"Email: `{new_email}`")
                        st.info(f"Password: `{new_password}`")
    
    with tab3:
        st.header("Subscription Management")
        
        # Subscription overview
        col1, col2, col3, col4 = st.columns(4)
        
        # Active subscriptions
        active_subs = get_single_value(
            "SELECT COUNT(*) FROM users WHERE subscription_status = 'active' AND subscription_end > NOW()"
        )
        with col1:
            st.metric("Active Subscriptions", active_subs or 0)
        
        # Expired subscriptions
        expired_subs = get_single_value(
            "SELECT COUNT(*) FROM users WHERE subscription_status = 'active' AND subscription_end < NOW()"
        )
        with col2:
            st.metric("Expired (Need Update)", expired_subs or 0)
        
        # Never subscribed
        never_subbed = get_single_value(
            "SELECT COUNT(*) FROM users WHERE subscription_status IS NULL OR (subscription_status = 'inactive' AND subscription_end IS NULL)"
        )
        with col3:
            st.metric("Never Subscribed", never_subbed or 0)
        
        # Total revenue (estimated)
        total_users_ever_active = get_single_value(
            "SELECT COUNT(*) FROM users WHERE subscription_end IS NOT NULL"
        )
        with col4:
            estimated_revenue = (total_users_ever_active or 0) * 25
            st.metric("Est. Total Revenue", f"£{estimated_revenue}")
        
        # Subscription actions
        st.subheader("🔧 Subscription Actions")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("🔄 Update Expired Subscriptions", type="primary"):
                count = execute_query(
                    """UPDATE users 
                    SET subscription_status = 'expired' 
                    WHERE subscription_status = 'active' 
                    AND subscription_end < NOW()"""
                )
                
                if count is not None:
                    st.success(f"Updated {count} expired subscriptions")
        
        with col2:
            if st.button("📊 Export Active Subscribers"):
                try:
                    with get_db_connection() as conn:
                        query = """
                            SELECT email, full_name, subscription_start, subscription_end,
                                   stripe_customer_id
                            FROM users 
                            WHERE subscription_status = 'active' 
                            ORDER BY subscription_end DESC
                        """
                        df = pd.read_sql(query, conn)
                        
                        if not df.empty:
                            csv = df.to_csv(index=False)
                            st.download_button(
                                label="📥 Download CSV",
                                data=csv,
                                file_name=f"active_subscribers_{datetime.now().strftime('%Y%m%d')}.csv",
                                mime="text/csv"
                            )
                        else:
                            st.info("No active subscribers to export")
                except Exception as e:
                    st.error(f"Export failed: {e}")
        
        # Subscription timeline
        st.subheader("📅 Subscription Timeline")
        
        timeframe = st.selectbox("View subscriptions expiring in:", 
                                 ["Next 7 days", "Next 30 days", "Next 90 days", "Already expired"])
        
        if timeframe == "Next 7 days":
            date_filter = "subscription_end BETWEEN NOW() AND NOW() + INTERVAL '7 days'"
        elif timeframe == "Next 30 days":
            date_filter = "subscription_end BETWEEN NOW() AND NOW() + INTERVAL '30 days'"
        elif timeframe == "Next 90 days":
            date_filter = "subscription_end BETWEEN NOW() AND NOW() + INTERVAL '90 days'"
        else:
            date_filter = "subscription_end < NOW()"
        
        query = f"""
            SELECT email, full_name, subscription_end, 
                   subscription_end - NOW() as days_remaining
            FROM users 
            WHERE subscription_status = 'active' AND {date_filter}
            ORDER BY subscription_end ASC
            LIMIT 20
        """
        
        expiring_users = execute_query(query, fetch=True)
        
        if expiring_users:
            for user in expiring_users:
                days = user['days_remaining'].days if user['days_remaining'].days >= 0 else 0
                
                col1, col2, col3 = st.columns([3, 1, 1])
                
                with col1:
                    if days == 0:
                        st.error(f"**{user['email']}** - Expired {abs(user['days_remaining'].days)} days ago")
                    elif days <= 7:
                        st.warning(f"**{user['email']}** - Expires in {days} days")
                    else:
                        st.info(f"**{user['email']}** - Expires in {days} days")
                
                with col2:
                    st.write(user['subscription_end'].strftime('%Y-%m-%d'))
                
                with col3:
                    if st.button("Extend 30d", key=f"extend_{user['email']}"):
                        new_end = user['subscription_end'] + timedelta(days=30)
                        execute_query(
                            "UPDATE users SET subscription_end = %s WHERE email = %s",
                            (new_end, user['email'])
                        )
                        st.success("Extended!")
                        time.sleep(1)
                        st.rerun()
        else:
            st.info(f"No subscriptions found for: {timeframe}")
    
    with tab4:
        st.header("Payment Management")
        
        # Payment statistics
        col1, col2, col3 = st.columns(3)
        
        # Total payments
        total_payments = get_single_value("SELECT COUNT(*) FROM payments")
        with col1:
            st.metric("Total Payments", total_payments or 0)
        
        # Completed payments
        completed_payments = get_single_value(
            "SELECT COUNT(*) FROM payments WHERE status = 'completed'"
        )
        with col2:
            st.metric("Completed", completed_payments or 0)
        
        # Pending payments
        pending_payments = get_single_value(
            "SELECT COUNT(*) FROM payments WHERE status = 'pending'"
        )
        with col3:
            st.metric("Pending", pending_payments or 0)
        
        # Recent payments
        st.subheader("💰 Recent Payments")
        
        payments = execute_query("""
            SELECT p.*, u.email, u.full_name
            FROM payments p
            JOIN users u ON p.user_id = u.user_id
            ORDER BY p.created_at DESC
            LIMIT 20
        """, fetch=True)
        
        if payments:
            for payment in payments:
                col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
                
                with col1:
                    st.write(f"**{payment['email']}** - {payment['full_name'] or 'No name'}")
                
                with col2:
                    st.write(f"£{payment['amount']}")
                
                with col3:
                    if payment['status'] == 'completed':
                        st.success(payment['status'])
                    else:
                        st.warning(payment['status'])
                
                with col4:
                    st.write(payment['created_at'].strftime('%Y-%m-%d %H:%M'))
                
                if payment['stripe_session_id']:
                    with st.expander(f"Session: {payment['stripe_session_id'][:20]}..."):
                        st.code(payment['stripe_session_id'])
                        
                        if st.button("🔍 Check in Stripe", key=f"stripe_{payment['payment_id']}"):
                            if "STRIPE_SECRET_KEY" in st.secrets:
                                try:
                                    stripe.api_key = st.secrets["STRIPE_SECRET_KEY"]
                                    session = stripe.checkout.Session.retrieve(payment['stripe_session_id'])
                                    st.json({
                                        "status": session.status,
                                        "payment_status": session.payment_status,
                                        "customer": session.customer,
                                        "amount": f"{session.amount_total/100} {session.currency}"
                                    })
                                except Exception as e:
                                    st.error(f"Stripe error: {e}")
        else:
            st.info("No payments found")
    
    with tab5:
        st.header("Database Tools")
        
        # Database info
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("📊 Database Information")
            
            # Database size
            db_size = get_single_value(
                "SELECT pg_size_pretty(pg_database_size(current_database()))"
            )
            st.metric("Database Size", db_size if db_size else "Unknown")
            
            # Active connections
            active_conns = get_single_value(
                "SELECT count(*) FROM pg_stat_activity WHERE state = 'active'"
            )
            st.metric("Active Connections", active_conns if active_conns else "Unknown")
            
            # PostgreSQL version
            pg_version = get_single_value("SELECT version()")
            if pg_version:
                st.text_area("PostgreSQL Version", pg_version, height=100)
        
        with col2:
            st.subheader("📋 Table Information")
            
            tables = execute_query("""
                SELECT 
                    tablename,
                    pg_size_pretty(pg_total_relation_size(quote_ident(tablename)::regclass)) as size,
                    (SELECT COUNT(*) FROM information_schema.columns 
                     WHERE table_name = tablename) as columns,
                    (SELECT COUNT(*) FROM pg_indexes 
                     WHERE tablename = t.tablename) as indexes
                FROM pg_tables t
                WHERE schemaname = 'public'
                ORDER BY pg_total_relation_size(quote_ident(tablename)::regclass) DESC
            """, fetch=True)
            
            if tables:
                df = pd.DataFrame(tables)
                st.dataframe(df, use_container_width=True)
        
        # Table schema checker
        st.subheader("🔍 Table Schema Checker")
        
        table_name = st.selectbox("Select table", ["users", "cvs", "analyses", "payments"])
        
        if st.button("Show Schema"):
            columns = execute_query("""
                SELECT 
                    column_name,
                    data_type,
                    character_maximum_length,
                    is_nullable,
                    column_default
                FROM information_schema.columns
                WHERE table_name = %s
                ORDER BY ordinal_position
            """, (table_name,), fetch=True)
            
            if columns:
                df = pd.DataFrame(columns)
                st.dataframe(df, use_container_width=True)
            else:
                st.error(f"Table '{table_name}' not found")
        
        # Missing columns checker
        st.subheader("🔧 Schema Integrity Check")
        
        if st.button("Check for Missing Columns"):
            # Define expected columns for each table
            expected_schema = {
                'users': ['user_id', 'email', 'password_hash', 'full_name', 'subscription_status',
                         'subscription_start', 'subscription_end', 'stripe_customer_id',
                         'stripe_subscription_id', 'created_at', 'last_login'],
                'cvs': ['cv_id', 'user_id', 'cv_name', 'cv_text', 'parsed_data', 'uploaded_at'],
                'analyses': ['analysis_id', 'user_id', 'cv_id', 'job_title', 'company',
                           'job_description', 'parsed_job', 'analysis_result', 'created_at'],
                'payments': ['payment_id', 'user_id', 'stripe_session_id', 'amount', 'status', 'created_at']
            }
            
            issues_found = False
            
            for table, expected_cols in expected_schema.items():
                # Get actual columns
                actual_cols_result = execute_query("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name = %s
                """, (table,), fetch=True)
                
                if actual_cols_result:
                    actual_cols = [col['column_name'] for col in actual_cols_result]
                    missing_cols = [col for col in expected_cols if col not in actual_cols]
                    
                    if missing_cols:
                        issues_found = True
                        st.warning(f"**{table}** is missing columns: {', '.join(missing_cols)}")
                        
                        # Offer to add missing columns
                        if st.button(f"Add missing columns to {table}", key=f"fix_{table}"):
                            for col in missing_cols:
                                # Determine column type
                                if col.endswith('_id') or col == 'user_id':
                                    col_type = "UUID"
                                elif col.endswith('_at') or col.endswith('_start') or col.endswith('_end'):
                                    col_type = "TIMESTAMP"
                                elif col in ['amount']:
                                    col_type = "DECIMAL(10,2)"
                                elif col in ['cv_text', 'job_description']:
                                    col_type = "TEXT"
                                elif col in ['parsed_data', 'parsed_job', 'analysis_result']:
                                    col_type = "JSONB"
                                else:
                                    col_type = "VARCHAR(255)"
                                
                                try:
                                    execute_query(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {col} {col_type}")
                                    st.success(f"Added {col} to {table}")
                                except Exception as e:
                                    st.error(f"Failed to add {col}: {e}")
                    else:
                        st.success(f"✅ {table} has all expected columns")
                else:
                    st.error(f"❌ Table {table} does not exist")
                    issues_found = True
            
            if not issues_found:
                st.success("✅ All tables have the expected schema!")
        
        # Query runner
        st.subheader("🔬 Query Runner")
        st.warning("⚠️ Use with caution! Only SELECT queries are allowed for safety.")
        
        query = st.text_area("SQL Query", height=150, placeholder="SELECT * FROM users LIMIT 10")
        
        col1, col2 = st.columns([1, 4])
        
        with col1:
            allow_write = st.checkbox("Allow write queries", value=False)
        
        with col2:
            if st.button("Execute Query", type="primary"):
                if query.strip():
                    # Safety check
                    if not allow_write and not query.strip().upper().startswith("SELECT"):
                        st.error("Only SELECT queries are allowed unless 'Allow write queries' is checked")
                    else:
                        try:
                            start_time = time.time()
                            
                            if query.strip().upper().startswith("SELECT"):
                                with get_db_connection() as conn:
                                    df = pd.read_sql(query, conn)
                                    elapsed = time.time() - start_time
                                    
                                    st.success(f"✅ Query executed in {elapsed:.2f} seconds")
                                    st.write(f"Returned {len(df)} rows")
                                    
                                    if len(df) > 0:
                                        st.dataframe(df, use_container_width=True)
                                        
                                        # Download option
                                        csv = df.to_csv(index=False)
                                        st.download_button(
                                            label="📥 Download as CSV",
                                            data=csv,
                                            file_name=f"query_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                                            mime="text/csv"
                                        )
                            else:
                                # Execute write query
                                result = execute_query(query)
                                elapsed = time.time() - start_time
                                
                                if result is not None:
                                    st.success(f"✅ Query executed in {elapsed:.2f} seconds")
                                    st.write(f"Affected {result} rows")
                                else:
                                    st.error("Query execution failed")
                            
                        except Exception as e:
                            st.error(f"Query error: {str(e)}")
                            if "permission denied" in str(e).lower():
                                st.info("This error usually means the database user doesn't have the required permissions")
    
    with tab6:
        st.header("Connection Debug")
        
        # Network information
        st.subheader("🌐 Network Information")
        
        col1, col2 = st.columns(2)
        
        with col1:
            try:
                hostname = socket.gethostname()
                local_ip = socket.gethostbyname(hostname)
                st.info(f"**Hostname:** {hostname}")
                st.info(f"**Local IP:** {local_ip}")
            except Exception as e:
                st.error(f"Network info error: {e}")
        
        with col2:
            try:
                public_ip = requests.get('https://api.ipify.org', timeout=5).text
                st.info(f"**Public IP:** {public_ip}")
                st.caption("This is the IP that external services see")
            except:
                st.warning("Could not determine public IP")
        
        # Configuration check
        st.subheader("🔐 Configuration Check")
        
        # Group configurations
        config_groups = {
            "Database": ["DB_HOST", "DB_PORT", "DB_NAME", "DB_USER", "DB_PASSWORD"],
            "Stripe": ["STRIPE_SECRET_KEY", "STRIPE_PRICE_ID", "STRIPE_WEBHOOK_SECRET"],
            "Application": ["APP_URL", "ADMIN_EMAILS", "ADMIN_PASSWORD"],
            "APIs": ["ANTHROPIC_API_KEY"],
            "Email (Optional)": ["EMAIL_PROVIDER", "FROM_EMAIL", "SENDGRID_API_KEY", "SMTP_HOST"]
        }
        
        for group_name, secrets in config_groups.items():
            st.write(f"**{group_name}**")
            
            missing = []
            for secret in secrets:
                if secret in st.secrets:
                    if secret.endswith("PASSWORD") or secret.endswith("KEY"):
                        st.success(f"✅ {secret} is configured (hidden)")
                    else:
                        value = st.secrets[secret]
                        if len(str(value)) > 50:
                            st.success(f"✅ {secret} = {str(value)[:50]}...")
                        else:
                            st.success(f"✅ {secret} = {value}")
                else:
                    if "(Optional)" in group_name:
                        st.info(f"ℹ️ {secret} not configured (optional)")
                    else:
                        st.error(f"❌ {secret} is missing")
                        missing.append(secret)
            
            if missing and "(Optional)" not in group_name:
                st.error(f"Missing required secrets in {group_name}: {', '.join(missing)}")
            
            st.markdown("---")
        
        # Connection tests
        st.subheader("🔌 Connection Tests")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("Test Database Connection", type="primary"):
                with st.spinner("Testing..."):
                    try:
                        # Test network connectivity first
                        host = st.secrets["DB_HOST"]
                        port = int(st.secrets["DB_PORT"])
                        
                        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        sock.settimeout(5)
                        result = sock.connect_ex((host, port))
                        sock.close()
                        
                        if result == 0:
                            st.success(f"✅ Network: Can reach {host}:{port}")
                            
                            # Test database connection
                            with get_db_connection() as conn:
                                with conn.cursor() as cur:
                                    cur.execute("SELECT current_database(), current_user, version()")
                                    db_info = cur.fetchone()
                                    
                                    st.success("✅ Database: Connected successfully")
                                    st.code(f"""
Database: {db_info[0]}
User: {db_info[1]}
Version: {db_info[2].split(',')[0]}
                                    """)
                        else:
                            st.error(f"❌ Network: Cannot reach {host}:{port}")
                            st.info("Check firewall rules and network configuration")
                        
                    except Exception as e:
                        st.error(f"Connection test failed: {e}")
                        if "timeout" in str(e).lower():
                            st.info("Timeout error suggests a firewall or network issue")
                        elif "authentication" in str(e).lower():
                            st.info("Authentication error - check username/password")
        
        with col2:
            if st.button("Test Stripe Connection", type="primary"):
                if "STRIPE_SECRET_KEY" in st.secrets:
                    with st.spinner("Testing..."):
                        try:
                            stripe.api_key = st.secrets["STRIPE_SECRET_KEY"]
                            
                            # Test account access
                            account = stripe.Account.retrieve()
                            st.success("✅ Stripe: Connected successfully")
                            
                            # Show account info
                            mode = "TEST" if "sk_test_" in st.secrets["STRIPE_SECRET_KEY"] else "LIVE"
                            st.code(f"""
Account ID: {account.id}
Mode: {mode}
Country: {account.country}
Currency: {account.default_currency}
                            """)
                            
                            # Test price retrieval
                            if "STRIPE_PRICE_ID" in st.secrets:
                                try:
                                    price = stripe.Price.retrieve(st.secrets["STRIPE_PRICE_ID"])
                                    st.success(f"✅ Price found: {price.unit_amount/100} {price.currency.upper()}")
                                except Exception as e:
                                    st.error(f"❌ Price not found: {e}")
                                    if "No such price" in str(e):
                                        st.info("Check that the price ID matches the API key mode (test/live)")
                            
                        except Exception as e:
                            st.error(f"Stripe test failed: {e}")
                            if "Invalid API Key" in str(e):
                                st.info("Check that your API key is correct and active")
                else:
                    st.warning("Stripe API key not configured")
    
    with tab7:
        st.header("Stripe Payment Debug")
        
        # Check for session_id in URL
        query_params = st.query_params
        if "session_id" in query_params:
            st.info(f"Found session_id in URL: {query_params['session_id']}")
            st.session_state['debug_session_id'] = query_params['session_id']
        
        # Session lookup
        st.subheader("🔍 Debug Stripe Session")
        
        session_id = st.text_input("Stripe Session ID", 
                                   value=st.session_state.get('debug_session_id', ''),
                                   placeholder="cs_test_...")
        
        if session_id and st.button("Analyze Session", type="primary"):
            if "STRIPE_SECRET_KEY" in st.secrets:
                stripe.api_key = st.secrets["STRIPE_SECRET_KEY"]
                
                try:
                    with st.spinner("Retrieving session details..."):
                        # Retrieve session with expansions
                        session = stripe.checkout.Session.retrieve(
                            session_id,
                            expand=['customer', 'subscription', 'line_items', 'payment_intent']
                        )
                        
                        # Display session info
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.write("**Session Status**")
                            st.info(f"Status: {session.status}")
                            st.info(f"Payment Status: {session.payment_status}")
                            
                            if session.customer_details:
                                st.write("**Customer Details**")
                                st.write(f"Email: {session.customer_details.email}")
                                if session.customer_details.name:
                                    st.write(f"Name: {session.customer_details.name}")
                        
                        with col2:
                            st.write("**Payment Info**")
                            st.info(f"Amount: {session.amount_total/100} {session.currency.upper()}")
                            if session.payment_intent:
                                st.info(f"Payment Intent: {session.payment_intent}")
                            if session.subscription:
                                st.info(f"Subscription: {session.subscription}")
                        
                        # Check metadata and user mapping
                        st.write("**User Mapping**")
                        
                        user_id = session.metadata.get('user_id') or session.client_reference_id
                        
                        if user_id:
                            st.success(f"User ID found: `{user_id}`")
                            
                            # Look up user in database
                            user = execute_query(
                                "SELECT * FROM users WHERE user_id = %s",
                                (user_id,),
                                fetch=True
                            )
                            
                            if user:
                                user = dict(user[0])
                                st.success("✅ User found in database")
                                
                                with st.expander("User Details"):
                                    st.write(f"**Email:** {user['email']}")
                                    st.write(f"**Name:** {user['full_name']}")
                                    st.write(f"**Status:** {user['subscription_status']}")
                                    if user['subscription_end']:
                                        st.write(f"**Sub End:** {user['subscription_end']}")
                                    st.write(f"**Stripe Customer:** {user['stripe_customer_id']}")
                                
                                # Offer to fix subscription
                                if session.payment_status == 'paid' and user['subscription_status'] != 'active':
                                    st.warning("⚠️ Payment successful but user not active!")
                                    
                                    if st.button("🔧 Fix Subscription", type="primary"):
                                        sub_end = datetime.now() + timedelta(days=30)
                                        result = execute_query(
                                            """UPDATE users 
                                            SET subscription_status = 'active',
                                                subscription_end = %s,
                                                stripe_customer_id = %s,
                                                subscription_start = COALESCE(subscription_start, NOW())
                                            WHERE user_id = %s""",
                                            (sub_end, session.customer, user_id)
                                        )
                                        
                                        if result is not None:
                                            st.success("✅ Subscription activated!")
                                            
                                            # Update payment record
                                            execute_query(
                                                "UPDATE payments SET status = 'completed' WHERE stripe_session_id = %s",
                                                (session_id,)
                                            )
                            else:
                                st.error("❌ User not found in database")
                                
                                # Try to find by email
                                if session.customer_details and session.customer_details.email:
                                    email_user = execute_query(
                                        "SELECT * FROM users WHERE email = %s",
                                        (session.customer_details.email.lower(),),
                                        fetch=True
                                    )
                                    
                                    if email_user:
                                        st.info(f"Found user by email: {email_user[0]['user_id']}")
                                        if st.button("Link to this user"):
                                            # Update user with correct IDs
                                            execute_query(
                                                """UPDATE users 
                                                SET stripe_customer_id = %s
                                                WHERE email = %s""",
                                                (session.customer, session.customer_details.email.lower())
                                            )
                                            st.success("User linked!")
                                            st.rerun()
                        else:
                            st.error("❌ No user_id found in session metadata")
                        
                        # Raw session data
                        with st.expander("Raw Session Data"):
                            # Convert to dict for display
                            session_dict = {
                                'id': session.id,
                                'status': session.status,
                                'payment_status': session.payment_status,
                                'customer': session.customer,
                                'customer_email': session.customer_details.email if session.customer_details else None,
                                'amount_total': session.amount_total,
                                'currency': session.currency,
                                'metadata': dict(session.metadata),
                                'client_reference_id': session.client_reference_id,
                                'subscription': session.subscription,
                                'payment_intent': session.payment_intent,
                                'created': datetime.fromtimestamp(session.created).isoformat()
                            }
                            st.json(session_dict)
                
                except stripe.error.InvalidRequestError as e:
                    st.error(f"Invalid session ID: {e}")
                except Exception as e:
                    st.error(f"Error: {e}")
                    st.code(traceback.format_exc())
            else:
                st.error("Stripe API key not configured")
        
        # Recent sessions
        st.subheader("📋 Recent Checkout Sessions")
        
        if st.button("Load Recent Sessions"):
            if "STRIPE_SECRET_KEY" in st.secrets:
                stripe.api_key = st.secrets["STRIPE_SECRET_KEY"]
                
                try:
                    sessions = stripe.checkout.Session.list(limit=20)
                    
                    for session in sessions.data:
                        created = datetime.fromtimestamp(session.created)
                        
                        col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
                        
                        with col1:
                            email = session.customer_details.email if session.customer_details else "No email"
                            st.write(f"**{email}**")
                            st.caption(f"{session.id[:20]}...")
                        
                        with col2:
                            st.write(created.strftime('%Y-%m-%d %H:%M'))
                        
                        with col3:
                            if session.payment_status == 'paid':
                                st.success(session.payment_status)
                            else:
                                st.warning(session.payment_status)
                        
                        with col4:
                            if st.button("Debug", key=f"debug_{session.id}"):
                                st.session_state['debug_session_id'] = session.id
                                st.rerun()
                
                except Exception as e:
                    st.error(f"Error loading sessions: {e}")
        
        # Create test checkout
        st.subheader("🧪 Create Test Checkout")
        
        col1, col2 = st.columns(2)
        
        with col1:
            test_email = st.text_input("Test Email", value="test@example.com")
            test_user_id = st.text_input("Test User ID", value=str(uuid.uuid4()))
        
        with col2:
            if st.button("Create Test Session", type="primary"):
                if "STRIPE_SECRET_KEY" in st.secrets and "STRIPE_PRICE_ID" in st.secrets:
                    stripe.api_key = st.secrets["STRIPE_SECRET_KEY"]
                    
                    try:
                        session = stripe.checkout.Session.create(
                            customer_email=test_email,
                            payment_method_types=['card'],
                            line_items=[{
                                'price': st.secrets["STRIPE_PRICE_ID"],
                                'quantity': 1,
                            }],
                            mode='subscription',
                            success_url=st.secrets["APP_URL"] + "?payment=success&session_id={CHECKOUT_SESSION_ID}",
                            cancel_url=st.secrets["APP_URL"] + "?payment=cancelled",
                            client_reference_id=test_user_id,
                            metadata={'user_id': test_user_id}
                        )
                        
                        st.success("✅ Test session created!")
                        st.code(f"Session ID: {session.id}")
                        st.markdown(f"[🛒 Go to Checkout]({session.url})")
                        
                        # Show test card numbers
                        with st.expander("Test Card Numbers"):
                            st.code("""
Successful payment: 4242 4242 4242 4242
Requires auth: 4000 0025 0000 3155
Declined: 4000 0000 0000 0002

Use any future expiry, any 3-digit CVC, any 5-digit postal code
                            """)
                    
                    except Exception as e:
                        st.error(f"Error creating session: {e}")
                else:
                    st.error("Missing Stripe configuration")
    
    with tab8:
        st.header("Email Tools")
        
        st.info("Email functionality is for debugging purposes in this admin panel")
        
        # Email configuration status
        st.subheader("📧 Email Configuration")
        
        email_provider = st.secrets.get("EMAIL_PROVIDER", "console")
        st.write(f"**Current Provider:** {email_provider}")
        
        if email_provider == "console":
            st.info("Emails are being logged to console (development mode)")
        elif email_provider == "sendgrid":
            if "SENDGRID_API_KEY" in st.secrets:
                st.success("✅ SendGrid configured")
            else:
                st.error("❌ SendGrid API key missing")
        elif email_provider == "smtp":
            required = ["SMTP_HOST", "SMTP_PORT", "SMTP_USERNAME", "SMTP_PASSWORD"]
            missing = [s for s in required if s not in st.secrets]
            if missing:
                st.error(f"❌ Missing SMTP settings: {', '.join(missing)}")
            else:
                st.success("✅ SMTP configured")
        
        # Test email sending
        st.subheader("📤 Send Test Email")
        
        with st.form("test_email"):
            recipient = st.text_input("Recipient Email", placeholder="user@example.com")
            subject = st.text_input("Subject", value="Test Email from CareerVertex")
            
            email_type = st.selectbox("Email Type", [
                "Custom Message",
                "Welcome Email (with login link)",
                "Payment Confirmation"
            ])
            
            if email_type == "Custom Message":
                message = st.text_area("Message", value="This is a test email from CareerVertex admin panel.")
            
            if st.form_submit_button("Send Email", type="primary"):
                if recipient:
                    if email_type == "Custom Message":
                        # Send custom email
                        html_body = f"""
                        <html>
                        <body style="font-family: Arial, sans-serif;">
                            <h2>{subject}</h2>
                            <p>{message}</p>
                            <hr>
                            <p style="color: #666; font-size: 12px;">
                                This is a test email sent from CareerVertex admin panel.
                            </p>
                        </body>
                        </html>
                        """
                        
                        from utils.email import EmailSender
                        sender = EmailSender()
                        
                        if sender.send(recipient, subject, html_body):
                            st.success(f"✅ Email sent to {recipient}")
                            if email_provider == "console":
                                st.info("Check your console/terminal for the email output")
                        else:
                            st.error("Failed to send email")
                    
                    elif email_type == "Welcome Email (with login link)":
                        # Generate a test token
                        from utils.email import send_login_email
                        test_token = f"test_token_{uuid.uuid4().hex}"
                        
                        if send_login_email(recipient, "Test User", test_token):
                            st.success(f"✅ Welcome email sent to {recipient}")
                            st.info(f"Login token: {test_token}")
                        else:
                            st.error("Failed to send welcome email")
                    
                    elif email_type == "Payment Confirmation":
                        from utils.email import send_payment_confirmation_email
                        
                        if send_payment_confirmation_email(recipient, "Test User"):
                            st.success(f"✅ Payment confirmation sent to {recipient}")
                        else:
                            st.error("Failed to send payment confirmation")
                else:
                    st.error("Please enter a recipient email")
        
        # Email logs
        st.subheader("📜 Recent Email Activity")
        st.info("Email logging would be implemented here if using a service like SendGrid that provides webhooks")
        
        # Email templates preview
        st.subheader("📄 Email Template Preview")
        
        template = st.selectbox("Select Template", ["Welcome Email", "Payment Confirmation"])
        
        if st.button("Preview Template"):
            if template == "Welcome Email":
                st.markdown("""
                ### Welcome Email Template
                
                **Subject:** Welcome to CareerVertex - Your Login Link
                
                **Content:**
                - Greeting with user's name
                - Thank you for subscribing
                - Secure login link (expires in 24 hours)
                - List of features available
                - Support contact information
                """)
            
            elif template == "Payment Confirmation":
                st.markdown("""
                ### Payment Confirmation Template
                
                **Subject:** Payment Confirmed - CareerVertex Pro
                
                **Content:**
                - Greeting with user's name
                - Payment confirmation
                - Subscription details (£25/month)
                - Note about receiving login email
                - Thank you message
                """)
