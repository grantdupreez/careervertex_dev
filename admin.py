import streamlit as st
import psycopg2
from datetime import datetime, timedelta
import pandas as pd
import bcrypt

st.set_page_config(page_title="CareerVertex Admin", page_icon="🔧", layout="wide")

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
                conn = psycopg2.connect(
                    dbname=st.secrets["DB_NAME"],
                    user=st.secrets["DB_USER"],
                    password=st.secrets["DB_PASSWORD"],
                    host=st.secrets["DB_HOST"],
                    port=st.secrets["DB_PORT"],
                    sslmode='require'
                )
                cur = conn.cursor()
                cur.execute("SELECT 1")
                cur.close()
                conn.close()
                st.success("✅ Database connection successful!")
            except Exception as e:
                st.error(f"❌ Connection failed: {e}")
        
        # Simple stats
        st.subheader("Quick Stats")
        if st.button("Load Stats"):
            col1, col2, col3 = st.columns(3)
            
            # Total users
            try:
                conn = psycopg2.connect(
                    dbname=st.secrets["DB_NAME"],
                    user=st.secrets["DB_USER"],
                    password=st.secrets["DB_PASSWORD"],
                    host=st.secrets["DB_HOST"],
                    port=st.secrets["DB_PORT"],
                    sslmode='require'
                )
                cur = conn.cursor()
                cur.execute("SELECT COUNT(*) FROM users")
                count = cur.fetchone()[0]
                cur.close()
                conn.close()
                with col1:
                    st.metric("Total Users", count)
            except Exception as e:
                with col1:
                    st.metric("Total Users", "Error")
            
            # Active subs
            try:
                conn = psycopg2.connect(
                    dbname=st.secrets["DB_NAME"],
                    user=st.secrets["DB_USER"],
                    password=st.secrets["DB_PASSWORD"],
                    host=st.secrets["DB_HOST"],
                    port=st.secrets["DB_PORT"],
                    sslmode='require'
                )
                cur = conn.cursor()
                cur.execute("SELECT COUNT(*) FROM users WHERE subscription_status = 'active'")
                count = cur.fetchone()[0]
                cur.close()
                conn.close()
                with col2:
                    st.metric("Active Subs", count)
            except Exception as e:
                with col2:
                    st.metric("Active Subs", "Error")
            
            # Total CVs
            try:
                conn = psycopg2.connect(
                    dbname=st.secrets["DB_NAME"],
                    user=st.secrets["DB_USER"],
                    password=st.secrets["DB_PASSWORD"],
                    host=st.secrets["DB_HOST"],
                    port=st.secrets["DB_PORT"],
                    sslmode='require'
                )
                cur = conn.cursor()
                cur.execute("SELECT COUNT(*) FROM cvs")
                count = cur.fetchone()[0]
                cur.close()
                conn.close()
                with col3:
                    st.metric("Total CVs", count)
            except Exception as e:
                with col3:
                    st.metric("Total CVs", "Error")
    
    with tab2:
        st.header("User Management")
        
        # Search form
        with st.form("user_search"):
            email_search = st.text_input("Search by email")
            submitted = st.form_submit_button("Search")
            
            if submitted:
                try:
                    conn = psycopg2.connect(
                        dbname=st.secrets["DB_NAME"],
                        user=st.secrets["DB_USER"],
                        password=st.secrets["DB_PASSWORD"],
                        host=st.secrets["DB_HOST"],
                        port=st.secrets["DB_PORT"],
                        sslmode='require'
                    )
                    cur = conn.cursor()
                    
                    if email_search:
                        cur.execute(
                            "SELECT user_id, email, full_name, subscription_status FROM users WHERE email ILIKE %s LIMIT 10",
                            (f"%{email_search}%",)
                        )
                    else:
                        cur.execute("SELECT user_id, email, full_name, subscription_status FROM users LIMIT 10")
                    
                    users = cur.fetchall()
                    cur.close()
                    conn.close()
                    
                    if users:
                        for user in users:
                            st.write(f"**{user[1]}** - {user[2] or 'No name'} - Status: {user[3] or 'Inactive'}")
                            
                            col1, col2 = st.columns(2)
                            with col1:
                                if st.button(f"Activate Sub", key=f"act_{user[0]}"):
                                    try:
                                        conn = psycopg2.connect(
                                            dbname=st.secrets["DB_NAME"],
                                            user=st.secrets["DB_USER"],
                                            password=st.secrets["DB_PASSWORD"],
                                            host=st.secrets["DB_HOST"],
                                            port=st.secrets["DB_PORT"],
                                            sslmode='require'
                                        )
                                        cur = conn.cursor()
                                        cur.execute(
                                            "UPDATE users SET subscription_status = 'active', subscription_end = %s WHERE user_id = %s",
                                            (datetime.now() + timedelta(days=30), user[0])
                                        )
                                        conn.commit()
                                        cur.close()
                                        conn.close()
                                        st.success("Activated!")
                                    except Exception as e:
                                        st.error(f"Failed: {e}")
                            
                            with col2:
                                if st.button(f"Reset Password", key=f"pwd_{user[0]}"):
                                    new_pwd = "password123"
                                    pwd_hash = bcrypt.hashpw(new_pwd.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                                    try:
                                        conn = psycopg2.connect(
                                            dbname=st.secrets["DB_NAME"],
                                            user=st.secrets["DB_USER"],
                                            password=st.secrets["DB_PASSWORD"],
                                            host=st.secrets["DB_HOST"],
                                            port=st.secrets["DB_PORT"],
                                            sslmode='require'
                                        )
                                        cur = conn.cursor()
                                        cur.execute(
                                            "UPDATE users SET password_hash = %s WHERE user_id = %s",
                                            (pwd_hash, user[0])
                                        )
                                        conn.commit()
                                        cur.close()
                                        conn.close()
                                        st.success(f"Password: {new_pwd}")
                                    except Exception as e:
                                        st.error(f"Failed: {e}")
                            
                            st.divider()
                    else:
                        st.info("No users found")
                        
                except Exception as e:
                    st.error(f"Search failed: {e}")
    
    with tab3:
        st.header("Subscription Management")
        
        if st.button("Show Active Subscriptions"):
            try:
                conn = psycopg2.connect(
                    dbname=st.secrets["DB_NAME"],
                    user=st.secrets["DB_USER"],
                    password=st.secrets["DB_PASSWORD"],
                    host=st.secrets["DB_HOST"],
                    port=st.secrets["DB_PORT"],
                    sslmode='require'
                )
                query = """
                    SELECT email, subscription_end 
                    FROM users 
                    WHERE subscription_status = 'active' 
                    ORDER BY subscription_end 
                    LIMIT 20
                """
                df = pd.read_sql(query, conn)
                conn.close()
                
                if not df.empty:
                    st.dataframe(df)
                else:
                    st.info("No active subscriptions")
                    
            except Exception as e:
                st.error(f"Failed to load: {e}")
        
        if st.button("Update Expired Subscriptions"):
            try:
                conn = psycopg2.connect(
                    dbname=st.secrets["DB_NAME"],
                    user=st.secrets["DB_USER"],
                    password=st.secrets["DB_PASSWORD"],
                    host=st.secrets["DB_HOST"],
                    port=st.secrets["DB_PORT"],
                    sslmode='require'
                )
                cur = conn.cursor()
                cur.execute(
                    "UPDATE users SET subscription_status = 'expired' WHERE subscription_status = 'active' AND subscription_end < NOW()"
                )
                count = cur.rowcount
                conn.commit()
                cur.close()
                conn.close()
                st.success(f"Updated {count} expired subscriptions")
            except Exception as e:
                st.error(f"Failed: {e}")
    
    with tab4:
        st.header("Database Tools")
        
        # Simple query runner
        st.subheader("Run Query")
        query = st.text_area("SQL Query (SELECT only)")
        
        if st.button("Execute"):
            if query.strip().upper().startswith("SELECT"):
                try:
                    conn = psycopg2.connect(
                        dbname=st.secrets["DB_NAME"],
                        user=st.secrets["DB_USER"],
                        password=st.secrets["DB_PASSWORD"],
                        host=st.secrets["DB_HOST"],
                        port=st.secrets["DB_PORT"],
                        sslmode='require'
                    )
                    df = pd.read_sql(query, conn)
                    conn.close()
                    st.dataframe(df)
                except Exception as e:
                    st.error(f"Query failed: {e}")
            else:
                st.error("Only SELECT queries allowed")
