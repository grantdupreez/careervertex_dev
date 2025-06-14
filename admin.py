import streamlit as st
import psycopg2
from psycopg2.extras import DictCursor
from datetime import datetime, timedelta
import pandas as pd
import bcrypt

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

ADMIN_PASSWORD = st.secrets.get("ADMIN_PASSWORD", "admin123")

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

def get_connection():
    """Get database connection - exactly like db_test.py"""
    return psycopg2.connect(
        dbname=st.secrets["DB_NAME"],
        user=st.secrets["DB_USER"],
        password=st.secrets["DB_PASSWORD"],
        host=st.secrets["DB_HOST"],
        port=st.secrets["DB_PORT"],
        sslmode='require'
    )

def main():
    """Main admin panel."""
    check_admin_auth()
    
    st.title("🔧 CareerVertex Admin Panel")
    
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

def show_dashboard():
    """Show admin dashboard with key metrics."""
    st.header("📊 Admin Dashboard")
    
    try:
        conn = get_connection()
        cur = conn.cursor(cursor_factory=DictCursor)
        
        # Key metrics
        col1, col2, col3, col4 = st.columns(4)
        
        # Total users
        cur.execute("SELECT COUNT(*) as count FROM users")
        total_users = cur.fetchone()['count']
        
        with col1:
            st.metric("Total Users", total_users)
        
        # Active subscriptions
        cur.execute("SELECT COUNT(*) as count FROM users WHERE subscription_status = 'active' AND subscription_end > NOW()")
        active_subs = cur.fetchone()['count']
        
        with col2:
            st.metric("Active Subscriptions", active_subs)
        
        # Total revenue
        cur.execute("SELECT COALESCE(SUM(amount), 0) as total FROM payments WHERE status = 'completed'")
        total_revenue = cur.fetchone()['total']
        
        with col3:
            st.metric("Total Revenue", f"£{total_revenue:.2f}")
        
        # CVs uploaded
        cur.execute("SELECT COUNT(*) as count FROM cvs")
        total_cvs = cur.fetchone()['count']
        
        with col4:
            st.metric("CVs Uploaded", total_cvs)
        
        # Recent users
        st.subheader("Recent Registrations")
        
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
        conn.close()
        
    except Exception as e:
        st.error(f"Database error: {e}")

def show_user_management():
    """User management interface."""
    st.header("👥 User Management")
    
    # Search
    search_email = st.text_input("Search by email (leave empty to show all)")
    
    if st.button("Search Users"):
        try:
            conn = get_connection()
            cur = conn.cursor(cursor_factory=DictCursor)
            
            if search_email:
                cur.execute(
                    "SELECT * FROM users WHERE email ILIKE %s ORDER BY created_at DESC LIMIT 50",
                    (f"%{search_email}%",)
                )
            else:
                cur.execute("SELECT * FROM users ORDER BY created_at DESC LIMIT 50")
            
            users = cur.fetchall()
            
            if users:
                st.write(f"Found {len(users)} users")
                
                for user in users:
                    with st.expander(f"{user['email']} - {user['full_name'] or 'No name'}"):
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.write(f"**Email:** {user['email']}")
                            st.write(f"**Name:** {user['full_name'] or 'Not set'}")
                            st.write(f"**Created:** {user['created_at']}")
                        
                        with col2:
                            st.write(f"**Status:** {user['subscription_status'] or 'Inactive'}")
                            st.write(f"**Sub End:** {user.get('subscription_end', 'N/A')}")
                        
                        # Simple actions
                        col1, col2, col3 = st.columns(3)
                        
                        with col1:
                            if st.button("Reset Password", key=f"pwd_{user['user_id']}"):
                                reset_user_password(user['user_id'], user['email'])
                        
                        with col2:
                            if st.button("Activate 30 Days", key=f"act_{user['user_id']}"):
                                activate_subscription(user['user_id'])
                        
                        with col3:
                            if st.button("Deactivate", key=f"deact_{user['user_id']}"):
                                deactivate_subscription(user['user_id'])
            else:
                st.info("No users found")
            
            cur.close()
            conn.close()
            
        except Exception as e:
            st.error(f"Database error: {e}")

def reset_user_password(user_id, email):
    """Reset user password."""
    try:
        new_password = "password123"
        password_hash = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("UPDATE users SET password_hash = %s WHERE user_id = %s", (password_hash, user_id))
        conn.commit()
        cur.close()
        conn.close()
        
        st.success(f"Password reset for {email} to: {new_password}")
    except Exception as e:
        st.error(f"Failed: {e}")

def activate_subscription(user_id):
    """Activate subscription for 30 days."""
    try:
        conn = get_connection()
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
        
        st.success("✅ Subscription activated for 30 days")
    except Exception as e:
        st.error(f"Failed: {e}")

def deactivate_subscription(user_id):
    """Deactivate subscription."""
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            UPDATE users 
            SET subscription_status = 'inactive'
            WHERE user_id = %s
        """, (user_id,))
        conn.commit()
        cur.close()
        conn.close()
        
        st.success("✅ Subscription deactivated")
    except Exception as e:
        st.error(f"Failed: {e}")

def show_subscription_management():
    """Subscription management interface."""
    st.header("💳 Subscription Management")
    
    try:
        conn = get_connection()
        cur = conn.cursor(cursor_factory=DictCursor)
        
        # Stats
        col1, col2, col3 = st.columns(3)
        
        cur.execute("SELECT COUNT(*) as count FROM users WHERE subscription_status = 'active' AND subscription_end > NOW()")
        active_count = cur.fetchone()['count']
        
        with col1:
            st.metric("Active Subscriptions", active_count)
        
        cur.execute("SELECT COUNT(*) as count FROM users WHERE subscription_status = 'active' AND subscription_end < NOW()")
        expired_count = cur.fetchone()['count']
        
        with col2:
            st.metric("Expired", expired_count)
        
        cur.execute("SELECT COALESCE(SUM(amount), 0) as total FROM payments WHERE status = 'completed' AND created_at > NOW() - INTERVAL '30 days'")
        monthly_revenue = cur.fetchone()['total']
        
        with col3:
            st.metric("Last 30 Days", f"£{monthly_revenue:.2f}")
        
        # Active subscriptions
        st.subheader("Active Subscriptions")
        
        cur.execute("""
            SELECT email, full_name, subscription_end
            FROM users
            WHERE subscription_status = 'active'
            ORDER BY subscription_end ASC
            LIMIT 20
        """)
        
        active_subs = cur.fetchall()
        
        if active_subs:
            df = pd.DataFrame(active_subs)
            st.dataframe(df, use_container_width=True)
        
        # Recent payments
        st.subheader("Recent Payments")
        
        cur.execute("""
            SELECT p.created_at, u.email, p.amount, p.status
            FROM payments p
            JOIN users u ON p.user_id = u.user_id
            ORDER BY p.created_at DESC
            LIMIT 20
        """)
        
        payments = cur.fetchall()
        
        if payments:
            df = pd.DataFrame(payments)
            st.dataframe(df, use_container_width=True)
        
        cur.close()
        conn.close()
        
    except Exception as e:
        st.error(f"Database error: {e}")

def show_analytics():
    """Show analytics and usage stats."""
    st.header("📈 Analytics")
    
    try:
        conn = get_connection()
        cur = conn.cursor(cursor_factory=DictCursor)
        
        # Stats
        col1, col2, col3 = st.columns(3)
        
        cur.execute("SELECT COUNT(*) as count FROM analyses")
        total_analyses = cur.fetchone()['count']
        
        with col1:
            st.metric("Total Analyses", total_analyses)
        
        cur.execute("SELECT COUNT(*) as count FROM analyses WHERE created_at > NOW() - INTERVAL '7 days'")
        recent_analyses = cur.fetchone()['count']
        
        with col2:
            st.metric("Last 7 Days", recent_analyses)
        
        cur.execute("SELECT COUNT(DISTINCT user_id) as count FROM analyses")
        active_users = cur.fetchone()['count']
        
        with col3:
            st.metric("Users with Analyses", active_users)
        
        # User growth
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
        conn.close()
        
    except Exception as e:
        st.error(f"Database error: {e}")

def show_database_tools():
    """Database maintenance tools."""
    st.header("🔧 Database Tools")
    
    # Test connection
    if st.button("Test Database Connection"):
        try:
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("SELECT version()")
            version = cur.fetchone()
            st.success(f"✅ Connected! PostgreSQL {version[0]}")
            cur.close()
            conn.close()
        except Exception as e:
            st.error(f"❌ Connection failed: {e}")
    
    # Export
    st.subheader("Data Export")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("Export Users CSV"):
            try:
                conn = get_connection()
                df = pd.read_sql("""
                    SELECT email, full_name, subscription_status, subscription_end, created_at
                    FROM users
                    ORDER BY created_at DESC
                """, conn)
                conn.close()
                
                csv = df.to_csv(index=False)
                st.download_button(
                    "Download Users",
                    csv,
                    f"users_{datetime.now().strftime('%Y%m%d')}.csv",
                    "text/csv"
                )
            except Exception as e:
                st.error(f"Export failed: {e}")
    
    with col2:
        if st.button("Export Payments CSV"):
            try:
                conn = get_connection()
                df = pd.read_sql("""
                    SELECT p.created_at, u.email, p.amount, p.status
                    FROM payments p
                    JOIN users u ON p.user_id = u.user_id
                    ORDER BY p.created_at DESC
                """, conn)
                conn.close()
                
                csv = df.to_csv(index=False)
                st.download_button(
                    "Download Payments",
                    csv,
                    f"payments_{datetime.now().strftime('%Y%m%d')}.csv",
                    "text/csv"
                )
            except Exception as e:
                st.error(f"Export failed: {e}")
    
    # Maintenance
    st.subheader("Maintenance")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("Update Expired Subscriptions"):
            try:
                conn = get_connection()
                cur = conn.cursor()
                cur.execute("""
                    UPDATE users 
                    SET subscription_status = 'expired'
                    WHERE subscription_status = 'active' 
                    AND subscription_end < NOW()
                """)
                count = cur.rowcount
                conn.commit()
                cur.close()
                conn.close()
                st.success(f"Updated {count} expired subscriptions")
            except Exception as e:
                st.error(f"Failed: {e}")
    
    with col2:
        if st.button("Clean Expired Tokens"):
            try:
                conn = get_connection()
                cur = conn.cursor()
                cur.execute("""
                    UPDATE users 
                    SET login_token = NULL, token_expires = NULL
                    WHERE token_expires < NOW()
                """)
                count = cur.rowcount
                conn.commit()
                cur.close()
                conn.close()
                st.success(f"Cleaned {count} tokens")
            except Exception as e:
                st.error(f"Failed: {e}")

if __name__ == "__main__":
    main()
