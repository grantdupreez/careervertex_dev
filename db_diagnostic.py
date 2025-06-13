import streamlit as st
import psycopg2
from psycopg2.extras import DictCursor
import traceback

st.title("Database Diagnostic Tool")

# Test basic connection
st.header("1. Basic Connection Test")
try:
    conn = psycopg2.connect(
        dbname=st.secrets["DB_NAME"],
        user=st.secrets["DB_USER"],
        password=st.secrets["DB_PASSWORD"],
        host=st.secrets["DB_HOST"],
        port=st.secrets["DB_PORT"],
        sslmode='require'
    )
    st.success("✅ Connected to database successfully!")
    
    # Test query
    cur = conn.cursor()
    cur.execute("SELECT version()")
    version = cur.fetchone()
    st.info(f"PostgreSQL version: {version[0]}")
    cur.close()
    conn.close()
    
except Exception as e:
    st.error(f"❌ Connection failed: {e}")
    st.stop()

# Test table creation
st.header("2. Table Creation Test")

# Get existing tables
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
    cur.execute("""
        SELECT tablename FROM pg_tables 
        WHERE schemaname = 'public'
        ORDER BY tablename
    """)
    
    existing_tables = [row[0] for row in cur.fetchall()]
    
    if existing_tables:
        st.info(f"Existing tables: {', '.join(existing_tables)}")
    else:
        st.warning("No tables found in database")
    
    cur.close()
    conn.close()
    
except Exception as e:
    st.error(f"Failed to list tables: {e}")

# Test creating each table individually
st.header("3. Individual Table Creation")

tables = {
    "users": """
        CREATE TABLE IF NOT EXISTS users (
            user_id UUID PRIMARY KEY,
            email VARCHAR(255) UNIQUE NOT NULL,
            password_hash VARCHAR(255) NOT NULL,
            full_name VARCHAR(255),
            subscription_status VARCHAR(50) DEFAULT 'inactive',
            subscription_end TIMESTAMP,
            stripe_customer_id VARCHAR(255),
            created_at TIMESTAMP DEFAULT NOW(),
            login_token VARCHAR(255),
            token_expires TIMESTAMP
        )
    """,
    "cvs": """
        CREATE TABLE IF NOT EXISTS cvs (
            cv_id UUID PRIMARY KEY,
            user_id UUID REFERENCES users(user_id) ON DELETE CASCADE,
            cv_name VARCHAR(255) NOT NULL,
            cv_text TEXT,
            parsed_data JSONB,
            uploaded_at TIMESTAMP DEFAULT NOW()
        )
    """,
    "analyses": """
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
        )
    """,
    "payments": """
        CREATE TABLE IF NOT EXISTS payments (
            payment_id UUID PRIMARY KEY,
            user_id UUID REFERENCES users(user_id) ON DELETE CASCADE,
            stripe_session_id VARCHAR(255),
            amount DECIMAL(10, 2),
            status VARCHAR(50),
            created_at TIMESTAMP DEFAULT NOW()
        )
    """
}

for table_name, create_query in tables.items():
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
        
        # Check if table exists
        cur.execute("""
            SELECT EXISTS (
                SELECT FROM pg_tables 
                WHERE schemaname = 'public' 
                AND tablename = %s
            )
        """, (table_name,))
        
        exists = cur.fetchone()[0]
        
        if exists:
            st.success(f"✅ Table '{table_name}' already exists")
        else:
            # Try to create table
            cur.execute(create_query)
            conn.commit()
            st.success(f"✅ Table '{table_name}' created successfully")
        
        cur.close()
        conn.close()
        
    except Exception as e:
        st.error(f"❌ Failed to create table '{table_name}': {e}")
        if "permission denied" in str(e).lower():
            st.warning("It seems you don't have CREATE permission on the database")
        elif "already exists" in str(e).lower():
            st.info(f"Table '{table_name}' already exists (this is OK)")
        else:
            st.code(traceback.format_exc())

# Test permissions
st.header("4. Permission Test")

permissions_test = {
    "SELECT": "SELECT 1",
    "INSERT": "INSERT INTO users (user_id, email, password_hash, full_name) VALUES (gen_random_uuid(), 'test@test.com', 'test', 'Test User') ON CONFLICT DO NOTHING",
    "UPDATE": "UPDATE users SET full_name = 'Test User Updated' WHERE email = 'test@test.com'",
    "DELETE": "DELETE FROM users WHERE email = 'test@test.com'"
}

for perm_name, query in permissions_test.items():
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
        
        # Skip INSERT/UPDATE/DELETE if users table doesn't exist
        if perm_name != "SELECT" and "users" not in existing_tables:
            st.warning(f"⚠️ Skipping {perm_name} test - users table doesn't exist")
            continue
        
        cur.execute(query)
        conn.commit()
        st.success(f"✅ {perm_name} permission OK")
        
        cur.close()
        conn.close()
        
    except Exception as e:
        if "permission denied" in str(e).lower():
            st.error(f"❌ No {perm_name} permission")
        else:
            st.warning(f"⚠️ {perm_name} test issue: {e}")

# Recommendations
st.header("5. Recommendations")

if "users" not in existing_tables:
    st.warning("""
    **Action Required:**
    1. Grant CREATE permission to your database user, OR
    2. Run the following SQL manually in your database:
    """)
    
    with st.expander("SQL to create all tables"):
        for table_name, create_query in tables.items():
            st.code(create_query, language="sql")
        
        st.code("""
-- Create indexes
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_token ON users(login_token);
CREATE INDEX IF NOT EXISTS idx_analyses_user ON analyses(user_id);
CREATE INDEX IF NOT EXISTS idx_cvs_user ON cvs(user_id);
        """, language="sql")

# Show connection string (masked)
st.header("6. Connection Details")
st.code(f"""
Host: {st.secrets['DB_HOST']}
Port: {st.secrets['DB_PORT']}
Database: {st.secrets['DB_NAME']}
User: {st.secrets['DB_USER']}
Password: {'*' * 8}
SSL Mode: require
""")

if st.button("Copy Connection String"):
    conn_str = f"postgresql://{st.secrets['DB_USER']}:{st.secrets['DB_PASSWORD']}@{st.secrets['DB_HOST']}:{st.secrets['DB_PORT']}/{st.secrets['DB_NAME']}?sslmode=require"
    st.code(conn_str)
