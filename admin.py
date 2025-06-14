import streamlit as st
import psycopg2
from psycopg2.extras import DictCursor
from datetime import datetime, timedelta
import pandas as pd
import bcrypt
import time
from functools import wraps
import socket

st.set_page_config(
    page_title="CareerVertex Admin",
    page_icon="🔧",
    layout="wide"
)

# Admin authentication
def get_admin_emails():
    """Get admin emails from secrets."""
    emails = st.secrets.get("ADMIN_EMAILS", "admin@careervertex.com")
    return [email.strip() for email in emails.split(",")]

ADMIN_PASSWORD = st.secrets.get("ADMIN_PASSWORD", "admin123")  # Change this!

# Database connection with caching
@st.cache_resource(ttl=60)  # Cache for 1 minute
def test_db_connectivity():
    """Test if database is reachable."""
    try:
        # Quick socket test first
        host = st.secrets["DB_HOST"]
        port = int(st.secrets["DB_PORT"])
        
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)  # 2 second timeout for quick test
        result = sock.connect_ex((host, port))
        sock.close()
        
        return result == 0
    except:
        return False

def with_db_connection(func):
    """Decorator to handle database connections and errors."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not test_db_connectivity():
            st.error("🔴 Database is currently unreachable. Please check your connection.")
            st.info("This could be due to network issues, firewall settings, or database maintenance.")
            return None
        
        try:
            # Quick connection with short timeout
            conn = psycopg2.connect(
                dbname=st.secrets["DB_NAME"],
                user=st.secrets["DB_USER"],
                password=st.secrets["DB_PASSWORD"],
                host=st.secrets["DB_HOST"],
                port=st.secrets["DB_PORT"],
                sslmode='require',
                connect_timeout=5,  # Short timeout
                options='-c statement_timeout=10000'  # 10 second query timeout
            )
            
            # Set connection to autocommit for read operations
            conn.autocommit = True
            
            result = func(conn, *args, **kwargs)
            conn.close()
            return result
            
        except psycopg2.OperationalError as e:
            st.error("🔴 Database connection failed")
            st.info("Try refreshing the page or check your network connection.")
            return None
        except Exception as e:
            st.error(f"Database error: {str(e)}")
            return None
    
    return wrapper

def check_admin_auth():
    """Simple admin authentication."""
    if 'admin_authenticated' not in st.session_state:
        st.session_state.admin_authenticated = False
    
    if not st.session_state.admin_authenticated:
        st.title("🔒 Admin Login")
        
        with st.form("admin_login"):
            email = st.text_input("Admin Email")
            password = st.text_input("Password", type="password")
            
            if st.form_submit_button("Login"):
                admin_emails = get_admin_emails()
                if email.lower() in [e.lower() for e in admin_emails] and password == ADMIN_PASSWORD:
                    st.session_state.admin_authenticated = True
                    st.success("✅ Admin access granted")
                    st.rerun()
                else:
                    st.error("Invalid credentials")
        
        st.stop()

def main():
    """Main admin panel."""
    check_admin_auth()
    
    st.title("🔧 CareerVertex Admin Panel")
    
    # Show connection status
    col1, col2 = st.columns([4, 1])
    with col2:
        if test_db_connectivity():
            st.success("🟢 DB Connected")
        else:
            st.error("🔴 DB Offline")
    
    # Sidebar navigation
    st.sidebar.title("Navigation")
    page = st.sidebar.radio("Go to", [
        "📊 Dashboard",
        "👥 User Management",
        "💳 Subscription Management",
        "📈 Analytics",
        "🔧 Database Tools",
        "🚪 Logout"
    ])
    
    if page == "🚪 Logout":
        st.session_state.admin_authenticated = False
        st.rerun()
    
    elif page == "📊 Dashboard":
        show_dashboard()
    
    elif page == "👥 User Management":
        show_user_management()
    
    elif page == "💳 Subscription Management":
        show_subscription_management()
    
    elif page == "📈 Analytics":
        show_analytics()
    
    elif page == "🔧 Database Tools":
        show_database_tools()

@with_db_connection
def show_dashboard(conn):
    """Show admin dashboard with key metrics."""
    st.header("📊 Admin Dashboard")
    
    if conn is None:
        return
    
    try:
        cur = conn.cursor(cursor_factory=DictCursor)
        
        # Key metrics - all in one query for efficiency
        cur.execute("""
            SELECT 
                (SELECT COUNT(*) FROM users) as total_users,
                (SELECT COUNT(*) FROM users WHERE subscription_status = 'active' AND subscription_end > NOW()) as active_subs,
                (SELECT COALESCE(SUM(amount), 0) FROM payments WHERE status = 'completed') as total_revenue,
                (SELECT COUNT(*) FROM cvs) as total_cvs
        """)
        
        metrics = cur.fetchone()
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Users", metrics['total_users'])
        
        with col2:
            st.metric("Active Subscriptions", metrics['active_subs'])
        
        with col3:
            st.metric("Total Revenue", f"£{metrics['total_revenue']:.2f}")
        
        with col4:
            st.metric("CVs Uploaded", metrics['total_cvs'])
        
        # Recent activity - limit query time
        st.subheader("Recent Activity")
        
        cur.execute("""
            SELECT email, full_name, created_at, subscription_status
            FROM users
            ORDER BY created_at DESC
            LIMIT 10
        """)
        
        recent_users = cur.fetchall()
        
        if recent_users:
            df = pd.DataFrame(recent_users)
            st.dataframe(df, use_container_width=True)
        
        cur.close()
        
    except Exception as e:
        st.error(f"Error loading dashboard: {e}")

@with_db_connection
def show_user_management(conn):
    """User management interface."""
    st.header("👥 User Management")
    
    if conn is None:
        return
    
    # Search/filter options
    col1, col2, col3 = st.columns(3)
    
    with col1:
        search_email = st.text_input("Search by email")
    
    with col2:
        filter_status = st.selectbox("Filter by status", ["All", "Active", "Inactive", "Expired"])
    
    with col3:
        st.write("")  # Spacer
        search_button = st.button("🔍 Search", use_container_width=True)
    
    if search_button or search_email or filter_status != "All":
        try:
            cur = conn.cursor(cursor_factory=DictCursor)
            
            # Build query
            query = "SELECT * FROM users WHERE 1=1"
            params = []
            
            if search_email:
                query += " AND email ILIKE %s"
                params.append(f"%{search_email}%")
            
            if filter_status == "Active":
                query += " AND subscription_status = 'active' AND subscription_end > NOW()"
            elif filter_status == "Inactive":
                query += " AND (subscription_status = 'inactive' OR subscription_status IS NULL)"
            elif filter_status == "Expired":
                query += " AND subscription_status = 'active' AND subscription_end < NOW()"
            
            query += " ORDER BY created_at DESC LIMIT 50"
            
            cur.execute(query, params)
            users = cur.fetchall()
            
            if users:
                st.subheader(f"Found {len(users)} users")
                
                # Use a simpler display for better performance
                for idx, user in enumerate(users):
                    with st.expander(f"{user['email']} - {user['full_name'] or 'No name'}"):
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.write(f"**User ID:** `{user['user_id']}`")
                            st.write(f"**Email:** {user['email']}")
                            st.write(f"**Name:** {user['full_name'] or 'Not set'}")
                            st.write(f"**Created:** {user['created_at']}")
                        
                        with col2:
                            st.write(f"**Status:** {user['subscription_status'] or 'Inactive'}")
                            st.write(f"**Sub End:** {user.get('subscription_end', 'N/A')}")
                            
                            # Quick action buttons
                            if st.button("💳 Activate 30 Days", key=f"act_{idx}"):
                                activate_subscription(user['user_id'])
                                st.rerun()
            else:
                st.info("No users found")
            
            cur.close()
            
        except Exception as e:
            st.error(f"Error: {e}")

def activate_subscription(user_id):
    """Quick function to activate subscription."""
    try:
        conn = psycopg2.connect(
            dbname=st.secrets["DB_NAME"],
            user=st.secrets["DB_USER"],
            password=st.secrets["DB_PASSWORD"],
            host=st.secrets["DB_HOST"],
            port=st.secrets["DB_PORT"],
            sslmode='require',
            connect_timeout=5
        )
        cur = conn.cursor()
        cur.execute("""
            UPDATE users 
            SET subscription_status = 'active',
                subscription_end = %s
            WHERE user_id = %s
        """, (datetime.now() + timedelta(days=30), user_id))
        conn.commit()
        cur.close()
        conn.close()
        st.success("✅ Subscription activated")
    except Exception as e:
        st.error(f"Failed to activate: {e}")

@with_db_connection
def show_subscription_management(conn):
    """Subscription management interface."""
    st.header("💳 Subscription Management")
    
    if conn is None:
        return
    
    try:
        cur = conn.cursor(cursor_factory=DictCursor)
        
        # Quick stats in one query
        cur.execute("""
            SELECT 
                (SELECT COUNT(*) FROM users WHERE subscription_status = 'active' AND subscription_end > NOW()) as active_count,
                (SELECT COUNT(*) FROM users WHERE subscription_status = 'active' AND subscription_end < NOW()) as expired_count,
                (SELECT COALESCE(SUM(amount), 0) FROM payments WHERE status = 'completed' AND created_at > NOW() - INTERVAL '30 days') as monthly_revenue
        """)
        
        stats = cur.fetchone()
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Active Subscriptions", stats['active_count'])
        
        with col2:
            st.metric("Expired (needs renewal)", stats['expired_count'])
        
        with col3:
            st.metric("Last 30 Days Revenue", f"£{stats['monthly_revenue']:.2f}")
        
        # Active subscriptions table
        st.subheader("Active Subscriptions")
        
        cur.execute("""
            SELECT email, full_name, subscription_end,
                   EXTRACT(DAY FROM (subscription_end - NOW())) as days_left
            FROM users
            WHERE subscription_status = 'active'
            ORDER BY subscription_end ASC
            LIMIT 20
        """)
        
        active_subs = cur.fetchall()
        
        if active_subs:
            df = pd.DataFrame(active_subs)
            st.dataframe(df, use_container_width=True)
        
        cur.close()
        
    except Exception as e:
        st.error(f"Error: {e}")

@with_db_connection
def show_analytics(conn):
    """Show analytics and usage stats."""
    st.header("📈 Analytics")
    
    if conn is None:
        return
    
    try:
        cur = conn.cursor(cursor_factory=DictCursor)
        
        # Usage stats
        col1, col2, col3 = st.columns(3)
        
        cur.execute("""
            SELECT 
                (SELECT COUNT(*) FROM analyses) as total_analyses,
                (SELECT COUNT(*) FROM analyses WHERE created_at > NOW() - INTERVAL '7 days') as recent_analyses,
                (SELECT COUNT(DISTINCT user_id) FROM analyses) as active_users
        """)
        
        stats = cur.fetchone()
        
        with col1:
            st.metric("Total Analyses", stats['total_analyses'])
        
        with col2:
            st.metric("Last 7 Days", stats['recent_analyses'])
        
        with col3:
            st.metric("Active Users", stats['active_users'])
        
        # Simple user growth chart
        st.subheader("User Growth (Last 30 Days)")
        
        cur.execute("""
            SELECT DATE(created_at) as date, COUNT(*) as new_users
            FROM users
            WHERE created_at > NOW() - INTERVAL '30 days'
            GROUP BY DATE(created_at)
            ORDER BY date
        """)
        
        growth_data = cur.fetchall()
        
        if growth_data:
            df = pd.DataFrame(growth_data)
            st.line_chart(df.set_index('date')['new_users'])
        
        cur.close()
        
    except Exception as e:
        st.error(f"Error: {e}")

@with_db_connection
def show_database_tools(conn):
    """Database maintenance tools."""
    st.header("🔧 Database Tools")
    
    # Connection test
    st.subheader("Connection Test")
    
    if st.button("🔍 Test Database Connection"):
        if conn:
            st.success("✅ Database connection is working")
            
            # Show connection info
            try:
                cur = conn.cursor()
                cur.execute("SELECT version()")
                version = cur.fetchone()
                st.info(f"PostgreSQL {version[0]}")
                cur.close()
            except Exception as e:
                st.error(f"Query error: {e}")
        else:
            st.error("❌ Cannot connect to database")
    
    # Export tools
    st.subheader("Data Export")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("📥 Export Users CSV"):
            export_users_csv(conn)
    
    with col2:
        if st.button("📥 Export Payments CSV"):
            export_payments_csv(conn)
    
    # Quick actions
    st.subheader("Quick Actions")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🧹 Clean Expired Tokens"):
            clean_expired_tokens()
    
    with col2:
        if st.button("🔄 Update Expired Subscriptions"):
            update_expired_subscriptions()

def export_users_csv(conn):
    """Export users to CSV."""
    if conn is None:
        st.error("Database connection required")
        return
    
    try:
        query = """
            SELECT email, full_name, subscription_status, 
                   subscription_end, created_at
            FROM users
            ORDER BY created_at DESC
        """
        df = pd.read_sql(query, conn)
        csv = df.to_csv(index=False)
        
        st.download_button(
            label="Download Users CSV",
            data=csv,
            file_name=f"users_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )
    except Exception as e:
        st.error(f"Export error: {e}")

def export_payments_csv(conn):
    """Export payments to CSV."""
    if conn is None:
        st.error("Database connection required")
        return
    
    try:
        query = """
            SELECT p.created_at, u.email, p.amount, p.status
            FROM payments p
            JOIN users u ON p.user_id = u.user_id
            ORDER BY p.created_at DESC
        """
        df = pd.read_sql(query, conn)
        csv = df.to_csv(index=False)
        
        st.download_button(
            label="Download Payments CSV",
            data=csv,
            file_name=f"payments_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )
    except Exception as e:
        st.error(f"Export error: {e}")

def clean_expired_tokens():
    """Clean expired tokens."""
    try:
        conn = psycopg2.connect(
            dbname=st.secrets["DB_NAME"],
            user=st.secrets["DB_USER"],
            password=st.secrets["DB_PASSWORD"],
            host=st.secrets["DB_HOST"],
            port=st.secrets["DB_PORT"],
            sslmode='require',
            connect_timeout=5
        )
        cur = conn.cursor()
        cur.execute("""
            UPDATE users 
            SET login_token = NULL, token_expires = NULL
            WHERE token_expires < NOW()
        """)
        cleaned = cur.rowcount
        conn.commit()
        cur.close()
        conn.close()
        st.success(f"✅ Cleaned {cleaned} expired tokens")
    except Exception as e:
        st.error(f"Error: {e}")

def update_expired_subscriptions():
    """Update expired subscription statuses."""
    try:
        conn = psycopg2.connect(
            dbname=st.secrets["DB_NAME"],
            user=st.secrets["DB_USER"],
            password=st.secrets["DB_PASSWORD"],
            host=st.secrets["DB_HOST"],
            port=st.secrets["DB_PORT"],
            sslmode='require',
            connect_timeout=5
        )
        cur = conn.cursor()
        cur.execute("""
            UPDATE users 
            SET subscription_status = 'expired'
            WHERE subscription_status = 'active' 
            AND subscription_end < NOW()
        """)
        updated = cur.rowcount
        conn.commit()
        cur.close()
        conn.close()
        st.success(f"✅ Updated {updated} expired subscriptions")
    except Exception as e:
        st.error(f"Error: {e}")

if __name__ == "__main__":
    main()
