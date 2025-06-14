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
ADMIN_EMAILS = st.secrets.get("ADMIN_EMAILS", ["admin@careervertex.com"]).split(",")
ADMIN_PASSWORD = st.secrets.get("ADMIN_PASSWORD", "admin123")  # Change this!

def get_connection():
    """Get database connection."""
    return psycopg2.connect(
        dbname=st.secrets["DB_NAME"],
        user=st.secrets["DB_USER"],
        password=st.secrets["DB_PASSWORD"],
        host=st.secrets["DB_HOST"],
        port=st.secrets["DB_PORT"],
        sslmode='require'
    )

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
                if email.lower() in [e.lower() for e in ADMIN_EMAILS] and password == ADMIN_PASSWORD:
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
        
        # Active subscriptions
        cur.execute("SELECT COUNT(*) as count FROM users WHERE subscription_status = 'active' AND subscription_end > NOW()")
        active_subs = cur.fetchone()['count']
        
        # Total revenue (completed payments)
        cur.execute("SELECT COALESCE(SUM(amount), 0) as total FROM payments WHERE status = 'completed'")
        total_revenue = cur.fetchone()['total']
        
        # CVs uploaded
        cur.execute("SELECT COUNT(*) as count FROM cvs")
        total_cvs = cur.fetchone()['count']
        
        with col1:
            st.metric("Total Users", total_users)
        
        with col2:
            st.metric("Active Subscriptions", active_subs)
        
        with col3:
            st.metric("Total Revenue", f"£{total_revenue:.2f}")
        
        with col4:
            st.metric("CVs Uploaded", total_cvs)
        
        # Recent activity
        st.subheader("Recent Activity")
        
        # Recent registrations
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
        st.error(f"Error loading dashboard: {e}")

def show_user_management():
    """User management interface."""
    st.header("👥 User Management")
    
    # Search/filter options
    col1, col2, col3 = st.columns(3)
    
    with col1:
        search_email = st.text_input("Search by email")
    
    with col2:
        filter_status = st.selectbox("Filter by status", ["All", "Active", "Inactive", "Expired"])
    
    with col3:
        st.write("")  # Spacer
        if st.button("🔍 Search", use_container_width=True):
            st.session_state.search_triggered = True
    
    # User list
    try:
        conn = get_connection()
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
            
            for user in users:
                with st.expander(f"{user['email']} - {user['full_name'] or 'No name'}"):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.write(f"**User ID:** {user['user_id']}")
                        st.write(f"**Email:** {user['email']}")
                        st.write(f"**Name:** {user['full_name'] or 'Not set'}")
                        st.write(f"**Created:** {user['created_at']}")
                        st.write(f"**Last Login:** {user.get('last_login', 'Never')}")
                    
                    with col2:
                        st.write(f"**Status:** {user['subscription_status'] or 'Inactive'}")
                        st.write(f"**Sub End:** {user.get('subscription_end', 'N/A')}")
                        st.write(f"**Stripe ID:** {user.get('stripe_customer_id', 'None')}")
                    
                    # Action buttons
                    st.markdown("---")
                    col1, col2, col3, col4 = st.columns(4)
                    
                    with col1:
                        if st.button("✏️ Edit", key=f"edit_{user['user_id']}"):
                            st.session_state.editing_user = user['user_id']
                    
                    with col2:
                        if st.button("🔑 Reset Password", key=f"reset_{user['user_id']}"):
                            new_password = "password123"  # Generate random password in production
                            password_hash = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                            
                            cur2 = conn.cursor()
                            cur2.execute("UPDATE users SET password_hash = %s WHERE user_id = %s", 
                                       (password_hash, user['user_id']))
                            conn.commit()
                            cur2.close()
                            
                            st.success(f"Password reset to: {new_password}")
                    
                    with col3:
                        if st.button("💳 Activate Sub", key=f"activate_{user['user_id']}"):
                            cur2 = conn.cursor()
                            cur2.execute("""
                                UPDATE users 
                                SET subscription_status = 'active',
                                    subscription_end = %s
                                WHERE user_id = %s
                            """, (datetime.now() + timedelta(days=30), user['user_id']))
                            conn.commit()
                            cur2.close()
                            
                            st.success("Subscription activated for 30 days")
                            st.rerun()
                    
                    with col4:
                        if st.button("🗑️ Delete", key=f"delete_{user['user_id']}"):
                            if st.checkbox(f"Confirm delete {user['email']}", key=f"confirm_{user['user_id']}"):
                                cur2 = conn.cursor()
                                cur2.execute("DELETE FROM users WHERE user_id = %s", (user['user_id'],))
                                conn.commit()
                                cur2.close()
                                
                                st.success("User deleted")
                                st.rerun()
        else:
            st.info("No users found")
        
        cur.close()
        conn.close()
        
    except Exception as e:
        st.error(f"Error: {e}")

def show_subscription_management():
    """Subscription management interface."""
    st.header("💳 Subscription Management")
    
    try:
        conn = get_connection()
        cur = conn.cursor(cursor_factory=DictCursor)
        
        # Subscription stats
        col1, col2, col3 = st.columns(3)
        
        # Active subscriptions
        cur.execute("""
            SELECT COUNT(*) as count 
            FROM users 
            WHERE subscription_status = 'active' 
            AND subscription_end > NOW()
        """)
        active_count = cur.fetchone()['count']
        
        # Expired subscriptions
        cur.execute("""
            SELECT COUNT(*) as count 
            FROM users 
            WHERE subscription_status = 'active' 
            AND subscription_end < NOW()
        """)
        expired_count = cur.fetchone()['count']
        
        # Monthly revenue
        cur.execute("""
            SELECT COALESCE(SUM(amount), 0) as total 
            FROM payments 
            WHERE status = 'completed' 
            AND created_at > NOW() - INTERVAL '30 days'
        """)
        monthly_revenue = cur.fetchone()['total']
        
        with col1:
            st.metric("Active Subscriptions", active_count)
        
        with col2:
            st.metric("Expired (needs renewal)", expired_count)
        
        with col3:
            st.metric("Last 30 Days Revenue", f"£{monthly_revenue:.2f}")
        
        # Subscription list
        st.subheader("Active Subscriptions")
        
        cur.execute("""
            SELECT u.*, p.created_at as last_payment_date, p.amount as last_payment_amount
            FROM users u
            LEFT JOIN LATERAL (
                SELECT * FROM payments 
                WHERE user_id = u.user_id 
                AND status = 'completed'
                ORDER BY created_at DESC 
                LIMIT 1
            ) p ON true
            WHERE u.subscription_status = 'active'
            ORDER BY u.subscription_end ASC
        """)
        
        active_subs = cur.fetchall()
        
        if active_subs:
            df_data = []
            for sub in active_subs:
                days_left = (sub['subscription_end'] - datetime.now()).days if sub['subscription_end'] else 0
                df_data.append({
                    'Email': sub['email'],
                    'Name': sub['full_name'],
                    'Expires': sub['subscription_end'],
                    'Days Left': days_left,
                    'Last Payment': sub.get('last_payment_date', 'N/A'),
                    'Amount': f"£{sub.get('last_payment_amount', 0):.2f}"
                })
            
            df = pd.DataFrame(df_data)
            st.dataframe(df, use_container_width=True)
        
        # Payment history
        st.subheader("Recent Payments")
        
        cur.execute("""
            SELECT p.*, u.email, u.full_name
            FROM payments p
            JOIN users u ON p.user_id = u.user_id
            ORDER BY p.created_at DESC
            LIMIT 20
        """)
        
        payments = cur.fetchall()
        
        if payments:
            payment_data = []
            for payment in payments:
                payment_data.append({
                    'Date': payment['created_at'],
                    'Email': payment['email'],
                    'Name': payment['full_name'],
                    'Amount': f"£{payment['amount']:.2f}",
                    'Status': payment['status'],
                    'Session ID': payment['stripe_session_id'][:20] + '...'
                })
            
            df = pd.DataFrame(payment_data)
            st.dataframe(df, use_container_width=True)
        
        cur.close()
        conn.close()
        
    except Exception as e:
        st.error(f"Error: {e}")

def show_analytics():
    """Show analytics and usage stats."""
    st.header("📈 Analytics")
    
    try:
        conn = get_connection()
        cur = conn.cursor(cursor_factory=DictCursor)
        
        # User growth chart
        st.subheader("User Growth")
        
        cur.execute("""
            SELECT DATE_TRUNC('day', created_at) as date, COUNT(*) as new_users
            FROM users
            WHERE created_at > NOW() - INTERVAL '30 days'
            GROUP BY date
            ORDER BY date
        """)
        
        growth_data = cur.fetchall()
        
        if growth_data:
            df = pd.DataFrame(growth_data)
            st.line_chart(df.set_index('date')['new_users'])
        
        # Usage stats
        st.subheader("Usage Statistics")
        
        col1, col2, col3 = st.columns(3)
        
        # Total analyses
        cur.execute("SELECT COUNT(*) as count FROM analyses")
        total_analyses = cur.fetchone()['count']
        
        # Analyses last 7 days
        cur.execute("""
            SELECT COUNT(*) as count 
            FROM analyses 
            WHERE created_at > NOW() - INTERVAL '7 days'
        """)
        recent_analyses = cur.fetchone()['count']
        
        # Average analyses per user
        cur.execute("""
            SELECT AVG(analysis_count) as avg
            FROM (
                SELECT user_id, COUNT(*) as analysis_count
                FROM analyses
                GROUP BY user_id
            ) counts
        """)
        avg_analyses = cur.fetchone()['avg'] or 0
        
        with col1:
            st.metric("Total Analyses", total_analyses)
        
        with col2:
            st.metric("Analyses (Last 7 Days)", recent_analyses)
        
        with col3:
            st.metric("Avg Analyses/User", f"{avg_analyses:.1f}")
        
        # Top users
        st.subheader("Top Users by Activity")
        
        cur.execute("""
            SELECT u.email, u.full_name, 
                   COUNT(DISTINCT a.analysis_id) as analyses_count,
                   COUNT(DISTINCT c.cv_id) as cvs_count
            FROM users u
            LEFT JOIN analyses a ON u.user_id = a.user_id
            LEFT JOIN cvs c ON u.user_id = c.user_id
            GROUP BY u.user_id, u.email, u.full_name
            ORDER BY analyses_count DESC
            LIMIT 10
        """)
        
        top_users = cur.fetchall()
        
        if top_users:
            df = pd.DataFrame(top_users)
            st.dataframe(df, use_container_width=True)
        
        cur.close()
        conn.close()
        
    except Exception as e:
        st.error(f"Error: {e}")

def show_database_tools():
    """Database maintenance tools."""
    st.header("🔧 Database Tools")
    
    # Export data
    st.subheader("Export Data")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("📥 Export Users CSV"):
            try:
                conn = get_connection()
                query = """
                    SELECT email, full_name, subscription_status, 
                           subscription_end, created_at, last_login
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
                
                conn.close()
            except Exception as e:
                st.error(f"Export error: {e}")
    
    with col2:
        if st.button("📥 Export Payments CSV"):
            try:
                conn = get_connection()
                query = """
                    SELECT p.created_at, u.email, p.amount, p.status, p.stripe_session_id
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
                
                conn.close()
            except Exception as e:
                st.error(f"Export error: {e}")
    
    # Database cleanup
    st.subheader("Database Cleanup")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🧹 Clean Expired Tokens"):
            try:
                conn = get_connection()
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
                
                st.success(f"Cleaned {cleaned} expired tokens")
            except Exception as e:
                st.error(f"Cleanup error: {e}")
    
    with col2:
        if st.button("🔄 Update Expired Subscriptions"):
            try:
                conn = get_connection()
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
                
                st.success(f"Updated {updated} expired subscriptions")
            except Exception as e:
                st.error(f"Update error: {e}")
    
    # SQL Query Tool
    st.subheader("SQL Query Tool")
    st.warning("⚠️ Be careful! This executes raw SQL on your database.")
    
    sql_query = st.text_area("Enter SQL Query", height=150)
    
    if st.button("🚀 Execute Query"):
        if sql_query:
            try:
                conn = get_connection()
                
                # Only allow SELECT queries for safety
                if sql_query.strip().upper().startswith("SELECT"):
                    df = pd.read_sql(sql_query, conn)
                    st.dataframe(df, use_container_width=True)
                else:
                    st.error("Only SELECT queries are allowed in this interface")
                
                conn.close()
            except Exception as e:
                st.error(f"Query error: {e}")

if __name__ == "__main__":
    main()
