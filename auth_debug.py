import streamlit as st
import psycopg2
from psycopg2.extras import DictCursor
import uuid
import bcrypt
from datetime import datetime
import traceback

st.title("Fixed Authentication Debug Test")

# Direct database connection function
def get_db_connection():
    """Get a direct database connection"""
    try:
        conn = psycopg2.connect(
            dbname=st.secrets["DB_NAME"],
            user=st.secrets["DB_USER"],
            password=st.secrets["DB_PASSWORD"],
            host=st.secrets["DB_HOST"],
            port=st.secrets["DB_PORT"],
            sslmode='require'
        )
        return conn
    except Exception as e:
        st.error(f"Connection failed: {str(e)}")
        return None

# Test database connection
st.header("1. Database Connection Test")
if st.button("Test Direct Connection"):
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor(cursor_factory=DictCursor)
            cursor.execute("SELECT 1 as test")
            result = cursor.fetchone()
            if result:
                st.success("✅ Direct database connection successful")
            cursor.close()
            conn.close()
        except Exception as e:
            st.error(f"Query failed: {str(e)}")

# Check if users table exists
st.header("2. Check Users Table")
if st.button("Check Table"):
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor(cursor_factory=DictCursor)
            cursor.execute(
                """
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'users'
                )
                """
            )
            result = cursor.fetchone()
            if result and result['exists']:
                st.success("✅ Users table exists")
                
                # Check table structure
                cursor.execute(
                    """
                    SELECT column_name, data_type, is_nullable 
                    FROM information_schema.columns 
                    WHERE table_name = 'users'
                    ORDER BY ordinal_position
                    """
                )
                columns = cursor.fetchall()
                if columns:
                    st.write("Table structure:")
                    for col in columns:
                        st.write(f"- {col['column_name']}: {col['data_type']} (nullable: {col['is_nullable']})")
            else:
                st.error("❌ Users table does not exist")
                
                # Try to create it
                if st.button("Create Users Table"):
                    cursor.execute("""
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
                            last_login TIMESTAMP
                        )
                    """)
                    conn.commit()
                    st.success("Table created!")
                    
            cursor.close()
            conn.close()
        except Exception as e:
            st.error(f"Error: {str(e)}")

# Test user registration
st.header("3. Test User Registration")
with st.form("test_register"):
    test_email = st.text_input("Test Email", value=f"test_{uuid.uuid4().hex[:8]}@example.com")
    test_password = st.text_input("Test Password", value="testpass123", type="password")
    test_name = st.text_input("Test Name", value="Test User")
    
    if st.form_submit_button("Register User"):
        st.write("Testing registration...")
        
        conn = get_db_connection()
        if conn:
            try:
                cursor = conn.cursor(cursor_factory=DictCursor)
                
                # Check if user exists
                cursor.execute("SELECT user_id FROM users WHERE email = %s", (test_email.lower(),))
                existing = cursor.fetchone()
                
                if existing:
                    st.error("User already exists!")
                else:
                    # Generate user data
                    user_id = str(uuid.uuid4())
                    password_hash = bcrypt.hashpw(test_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                    
                    # Insert user
                    cursor.execute(
                        """
                        INSERT INTO users (user_id, email, password_hash, full_name, created_at)
                        VALUES (%s, %s, %s, %s, %s)
                        RETURNING user_id
                        """,
                        (user_id, test_email.lower(), password_hash, test_name, datetime.now())
                    )
                    
                    # Commit the transaction
                    conn.commit()
                    
                    # Verify the insert
                    cursor.execute("SELECT * FROM users WHERE user_id = %s", (user_id,))
                    new_user = cursor.fetchone()
                    
                    if new_user:
                        st.success(f"✅ User registered successfully!")
                        st.json(dict(new_user))
                    else:
                        st.error("❌ User registration verification failed")
                        
                cursor.close()
                conn.close()
                
            except Exception as e:
                st.error(f"Registration failed: {str(e)}")
                traceback.print_exc()
                if conn:
                    conn.rollback()

# Test user login
st.header("4. Test User Login")
with st.form("test_login"):
    login_email = st.text_input("Email to test")
    login_password = st.text_input("Password", type="password")
    
    if st.form_submit_button("Test Login"):
        conn = get_db_connection()
        if conn:
            try:
                cursor = conn.cursor(cursor_factory=DictCursor)
                
                # Get user
                cursor.execute(
                    "SELECT * FROM users WHERE email = %s",
                    (login_email.lower(),)
                )
                user = cursor.fetchone()
                
                if user:
                    st.success(f"✅ User found: {user['user_id']}")
                    
                    # Test password
                    if bcrypt.checkpw(login_password.encode('utf-8'), user['password_hash'].encode('utf-8')):
                        st.success("✅ Password correct! Login successful!")
                        
                        # Update last login
                        cursor.execute(
                            "UPDATE users SET last_login = %s WHERE user_id = %s",
                            (datetime.now(), user['user_id'])
                        )
                        conn.commit()
                        
                        st.json(dict(user))
                    else:
                        st.error("❌ Invalid password")
                else:
                    st.error("❌ User not found")
                    
                cursor.close()
                conn.close()
                
            except Exception as e:
                st.error(f"Login error: {str(e)}")
                traceback.print_exc()

# List existing users
st.header("5. List Existing Users")
if st.button("List Users"):
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor(cursor_factory=DictCursor)
            cursor.execute(
                "SELECT user_id, email, full_name, created_at, last_login FROM users ORDER BY created_at DESC LIMIT 10"
            )
            users = cursor.fetchall()
            
            if users:
                st.write(f"Found {len(users)} users:")
                for user in users:
                    st.write(f"- **{user['email']}** ({user['full_name']}) - Created: {user['created_at']}")
            else:
                st.info("No users found")
                
            cursor.close()
            conn.close()
        except Exception as e:
            st.error(f"Error listing users: {str(e)}")

# Quick user management
st.header("6. Quick User Management")
user_email_to_manage = st.text_input("Enter user email to manage")

col1, col2, col3 = st.columns(3)

with col1:
    if st.button("View User"):
        if user_email_to_manage:
            conn = get_db_connection()
            if conn:
                try:
                    cursor = conn.cursor(cursor_factory=DictCursor)
                    cursor.execute("SELECT * FROM users WHERE email = %s", (user_email_to_manage.lower(),))
                    user = cursor.fetchone()
                    
                    if user:
                        st.json(dict(user))
                    else:
                        st.error("User not found")
                        
                    cursor.close()
                    conn.close()
                except Exception as e:
                    st.error(f"Error: {str(e)}")

with col2:
    if st.button("Reset Password"):
        if user_email_to_manage:
            conn = get_db_connection()
            if conn:
                try:
                    cursor = conn.cursor(cursor_factory=DictCursor)
                    
                    # Generate new password
                    new_password = f"reset_{uuid.uuid4().hex[:8]}"
                    password_hash = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                    
                    # Update password
                    cursor.execute(
                        "UPDATE users SET password_hash = %s WHERE email = %s",
                        (password_hash, user_email_to_manage.lower())
                    )
                    
                    if cursor.rowcount > 0:
                        conn.commit()
                        st.success(f"Password reset to: **{new_password}**")
                    else:
                        st.error("User not found")
                        
                    cursor.close()
                    conn.close()
                except Exception as e:
                    st.error(f"Error: {str(e)}")

with col3:
    if st.button("Delete User"):
        if user_email_to_manage:
            if st.checkbox("Confirm deletion"):
                conn = get_db_connection()
                if conn:
                    try:
                        cursor = conn.cursor(cursor_factory=DictCursor)
                        
                        # Get user ID first
                        cursor.execute("SELECT user_id FROM users WHERE email = %s", (user_email_to_manage.lower(),))
                        user = cursor.fetchone()
                        
                        if user:
                            user_id = user['user_id']
                            
                            # Delete related records
                            cursor.execute("DELETE FROM token_usage WHERE user_id = %s", (user_id,))
                            cursor.execute("DELETE FROM analyses WHERE user_id = %s", (user_id,))
                            cursor.execute("DELETE FROM job_descriptions WHERE user_id = %s", (user_id,))
                            cursor.execute("DELETE FROM cvs WHERE user_id = %s", (user_id,))
                            cursor.execute("DELETE FROM payments WHERE user_id = %s", (user_id,))
                            cursor.execute("DELETE FROM users WHERE user_id = %s", (user_id,))
                            
                            conn.commit()
                            st.success("User deleted successfully")
                        else:
                            st.error("User not found")
                            
                        cursor.close()
                        conn.close()
                    except Exception as e:
                        st.error(f"Error: {str(e)}")

# Connection pool info
st.header("7. Connection Info")
if st.button("Show Connection Details"):
    st.code(f"""
    Database: {st.secrets.get('DB_NAME', 'Not set')}
    Host: {st.secrets.get('DB_HOST', 'Not set')}
    Port: {st.secrets.get('DB_PORT', 'Not set')}
    User: {st.secrets.get('DB_USER', 'Not set')}
    SSL Mode: require
    """)

# Create test user for main app
st.header("8. Create Test User for Main App")
with st.form("create_app_user"):
    app_email = st.text_input("Email", value="demo@example.com")
    app_password = st.text_input("Password", value="demo123", type="password")
    app_name = st.text_input("Full Name", value="Demo User")
    
    if st.form_submit_button("Create User for App", type="primary"):
        conn = get_db_connection()
        if conn:
            try:
                cursor = conn.cursor(cursor_factory=DictCursor)
                
                # Check if exists
                cursor.execute("SELECT user_id FROM users WHERE email = %s", (app_email.lower(),))
                if cursor.fetchone():
                    st.warning("User already exists!")
                else:
                    # Create user
                    user_id = str(uuid.uuid4())
                    password_hash = bcrypt.hashpw(app_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                    
                    cursor.execute(
                        """
                        INSERT INTO users (user_id, email, password_hash, full_name, created_at)
                        VALUES (%s, %s, %s, %s, %s)
                        """,
                        (user_id, app_email.lower(), password_hash, app_name, datetime.now())
                    )
                    conn.commit()
                    
                    st.success(f"✅ User created successfully!")
                    st.info(f"You can now login to the main app with:")
                    st.code(f"Email: {app_email}\nPassword: {app_password}")
                    
                cursor.close()
                conn.close()
            except Exception as e:
                st.error(f"Error: {str(e)}")
                if conn:
                    conn.rollback()
