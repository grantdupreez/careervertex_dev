import streamlit as st
from db_manager import DatabaseManager
from auth_manager import AuthManager
import uuid
import bcrypt
from datetime import datetime

st.title("Authentication Debug Test")

# Initialize database manager
db_manager = DatabaseManager()
auth_manager = AuthManager(db_manager)

# Test database connection
st.header("1. Database Connection Test")
if st.button("Test Connection"):
    try:
        result = db_manager.execute_query("SELECT 1 as test")
        if result:
            st.success("✅ Database connection successful")
        else:
            st.error("❌ Database query returned None")
    except Exception as e:
        st.error(f"❌ Database connection failed: {str(e)}")

# Check if users table exists
st.header("2. Check Users Table")
if st.button("Check Table"):
    try:
        result = db_manager.execute_query(
            """
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'users'
            )
            """
        )
        if result and result[0]['exists']:
            st.success("✅ Users table exists")
            
            # Check table structure
            columns = db_manager.execute_query(
                """
                SELECT column_name, data_type, is_nullable 
                FROM information_schema.columns 
                WHERE table_name = 'users'
                ORDER BY ordinal_position
                """
            )
            if columns:
                st.write("Table structure:")
                for col in columns:
                    st.write(f"- {col['column_name']}: {col['data_type']} (nullable: {col['is_nullable']})")
        else:
            st.error("❌ Users table does not exist")
    except Exception as e:
        st.error(f"Error checking table: {str(e)}")

# Test user registration
st.header("3. Test User Registration")
with st.form("test_register"):
    test_email = st.text_input("Test Email", value=f"test_{uuid.uuid4().hex[:8]}@example.com")
    test_password = st.text_input("Test Password", value="testpass123", type="password")
    test_name = st.text_input("Test Name", value="Test User")
    
    if st.form_submit_button("Test Registration"):
        st.write("Testing registration...")
        
        # Try direct database insert first
        try:
            # Generate test data
            user_id = str(uuid.uuid4())
            password_hash = bcrypt.hashpw(test_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            
            # Direct insert
            result = db_manager.execute_query(
                """
                INSERT INTO users (user_id, email, password_hash, full_name, created_at)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING user_id
                """,
                (user_id, test_email, password_hash, test_name, datetime.now()),
                fetch=True,
                commit=True
            )
            
            if result:
                st.success(f"✅ Direct insert successful! User ID: {result[0]['user_id']}")
            else:
                st.error("❌ Direct insert returned None")
                
        except Exception as e:
            st.error(f"❌ Direct insert failed: {str(e)}")
            import traceback
            st.code(traceback.format_exc())
        
        # Now try through AuthManager
        st.write("\nTesting through AuthManager...")
        try:
            success, result = auth_manager.register_user(test_email + "_auth", test_password, test_name)
            if success:
                st.success(f"✅ AuthManager registration successful! User ID: {result}")
            else:
                st.error(f"❌ AuthManager registration failed: {result}")
        except Exception as e:
            st.error(f"❌ AuthManager error: {str(e)}")
            import traceback
            st.code(traceback.format_exc())

# Test user login
st.header("4. Test User Login")
with st.form("test_login"):
    login_email = st.text_input("Email to test")
    login_password = st.text_input("Password", type="password")
    
    if st.form_submit_button("Test Login"):
        # First check if user exists
        try:
            user_check = db_manager.execute_query(
                "SELECT user_id, email, password_hash FROM users WHERE email = %s",
                (login_email,)
            )
            
            if user_check:
                st.success(f"✅ User found: {user_check[0]['user_id']}")
                st.write(f"Password hash starts with: {user_check[0]['password_hash'][:20]}...")
                
                # Test password verification
                if bcrypt.checkpw(login_password.encode('utf-8'), user_check[0]['password_hash'].encode('utf-8')):
                    st.success("✅ Password verification successful")
                else:
                    st.error("❌ Password verification failed")
            else:
                st.error("❌ User not found")
                
        except Exception as e:
            st.error(f"Error checking user: {str(e)}")
        
        # Test through AuthManager
        st.write("\nTesting through AuthManager...")
        try:
            success, result = auth_manager.login_user(login_email, login_password)
            if success:
                st.success("✅ AuthManager login successful!")
                st.json(result)
            else:
                st.error(f"❌ AuthManager login failed: {result}")
        except Exception as e:
            st.error(f"❌ AuthManager error: {str(e)}")
            import traceback
            st.code(traceback.format_exc())

# List existing users
st.header("5. List Existing Users")
if st.button("List Users"):
    try:
        users = db_manager.execute_query(
            "SELECT user_id, email, full_name, created_at FROM users ORDER BY created_at DESC LIMIT 10"
        )
        
        if users:
            st.write(f"Found {len(users)} users:")
            for user in users:
                st.write(f"- {user['email']} ({user['full_name']}) - Created: {user['created_at']}")
        else:
            st.info("No users found")
    except Exception as e:
        st.error(f"Error listing users: {str(e)}")

# Test execute_query with different parameters
st.header("6. Test Query Execution")
if st.button("Test Various Queries"):
    st.subheader("Test 1: Simple SELECT")
    try:
        result = db_manager.execute_query("SELECT NOW() as current_time")
        st.success(f"Current time: {result[0]['current_time']}")
    except Exception as e:
        st.error(f"Failed: {str(e)}")
    
    st.subheader("Test 2: INSERT with RETURNING")
    try:
        test_id = str(uuid.uuid4())
        result = db_manager.execute_query(
            """
            INSERT INTO users (user_id, email, password_hash, full_name, created_at)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING user_id
            """,
            (test_id, f"query_test_{test_id[:8]}@example.com", "dummy_hash", "Query Test", datetime.now()),
            fetch=True,
            commit=True
        )
        if result:
            st.success(f"Insert successful: {result[0]['user_id']}")
        else:
            st.error("Insert returned None")
    except Exception as e:
        st.error(f"Failed: {str(e)}")
    
    st.subheader("Test 3: UPDATE")
    if result:
        try:
            update_result = db_manager.execute_query(
                "UPDATE users SET full_name = %s WHERE user_id = %s",
                ("Updated Name", test_id),
                fetch=False,
                commit=True
            )
            st.success(f"Update result: {update_result}")
        except Exception as e:
            st.error(f"Failed: {str(e)}")

# Check for common issues
st.header("7. Common Issues Check")
if st.button("Run Diagnostics"):
    issues = []
    
    # Check connection
    try:
        conn = db_manager.get_connection()
        if conn:
            conn.close()
            st.success("✅ Can create connections")
        else:
            issues.append("Cannot create database connections")
    except Exception as e:
        issues.append(f"Connection error: {str(e)}")
    
    # Check commit mode
    try:
        # Test with explicit commit
        test_id = str(uuid.uuid4())
        result = db_manager.execute_query(
            "INSERT INTO users (user_id, email, password_hash, full_name) VALUES (%s, %s, %s, %s)",
            (test_id, f"commit_test_{test_id[:8]}@example.com", "test", "Commit Test"),
            fetch=False,
            commit=True
        )
        
        # Verify insert
        check = db_manager.execute_query(
            "SELECT user_id FROM users WHERE user_id = %s",
            (test_id,)
        )
        
        if check:
            st.success("✅ Commits are working")
        else:
            issues.append("Commits may not be working properly")
            
    except Exception as e:
        issues.append(f"Commit test failed: {str(e)}")
    
    if issues:
        st.error("Issues found:")
        for issue in issues:
            st.write(f"- {issue}")
    else:
        st.success("✅ No issues detected")
