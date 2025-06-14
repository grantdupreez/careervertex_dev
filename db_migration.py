import streamlit as st
import psycopg2
from psycopg2.extras import DictCursor

st.title("Database Migration Tool")

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

# Check current schema
st.header("1. Current Users Table Schema")
try:
    conn = get_connection()
    cur = conn.cursor(cursor_factory=DictCursor)
    
    # Get column information
    cur.execute("""
        SELECT column_name, data_type, is_nullable
        FROM information_schema.columns
        WHERE table_name = 'users'
        ORDER BY ordinal_position
    """)
    
    columns = cur.fetchall()
    
    st.write("Current columns:")
    for col in columns:
        st.write(f"- {col['column_name']}: {col['data_type']} (nullable: {col['is_nullable']})")
    
    cur.close()
    conn.close()
    
except Exception as e:
    st.error(f"Error checking schema: {e}")

# Add missing columns
st.header("2. Add Missing Columns")

missing_columns = {
    'last_login': 'TIMESTAMP',
    'subscription_start': 'TIMESTAMP',
    'stripe_subscription_id': 'VARCHAR(255)'
}

if st.button("Check and Add Missing Columns"):
    try:
        conn = get_connection()
        cur = conn.cursor()
        
        # Check which columns exist
        cur.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'users'
        """)
        
        existing_columns = [row[0] for row in cur.fetchall()]
        
        # Add missing columns
        for column_name, column_type in missing_columns.items():
            if column_name not in existing_columns:
                st.write(f"Adding column: {column_name}")
                try:
                    cur.execute(f"ALTER TABLE users ADD COLUMN {column_name} {column_type}")
                    conn.commit()
                    st.success(f"✅ Added column: {column_name}")
                except psycopg2.errors.DuplicateColumn:
                    st.info(f"Column {column_name} already exists")
                except Exception as e:
                    st.error(f"Failed to add {column_name}: {e}")
                    conn.rollback()
            else:
                st.info(f"✅ Column {column_name} already exists")
        
        cur.close()
        conn.close()
        
        st.success("✅ Schema update complete!")
        
    except Exception as e:
        st.error(f"Migration error: {e}")

# Fix subscription status
st.header("3. Fix User Subscription Status")

user_email = st.text_input("Enter user email to check/fix")

if user_email and st.button("Check User"):
    try:
        conn = get_connection()
        cur = conn.cursor(cursor_factory=DictCursor)
        
        # Get user info
        cur.execute("SELECT * FROM users WHERE email = %s", (user_email.lower(),))
        user = cur.fetchone()
        
        if user:
            st.write("User found:")
            st.json(dict(user))
            
            # Check payments
            cur.execute("""
                SELECT * FROM payments 
                WHERE user_id = %s 
                ORDER BY created_at DESC
                LIMIT 5
            """, (user['user_id'],))
            
            payments = cur.fetchall()
            if payments:
                st.write("Recent payments:")
                for payment in payments:
                    st.write(f"- {payment['created_at']}: {payment['status']} (Session: {payment['stripe_session_id'][:20]}...)")
            
            # Fix subscription if needed
            if st.button("Activate Subscription (30 days)"):
                from datetime import datetime, timedelta
                
                cur.execute("""
                    UPDATE users 
                    SET subscription_status = 'active',
                        subscription_end = %s,
                        subscription_start = COALESCE(subscription_start, NOW())
                    WHERE user_id = %s
                """, (datetime.now() + timedelta(days=30), user['user_id']))
                
                conn.commit()
                st.success("✅ Subscription activated!")
        else:
            st.error("User not found")
        
        cur.close()
        conn.close()
        
    except Exception as e:
        st.error(f"Error: {e}")

# Show SQL to run manually
st.header("4. Manual SQL (if needed)")

with st.expander("Show SQL commands"):
    st.code("""
-- Add missing columns to users table
ALTER TABLE users ADD COLUMN IF NOT EXISTS last_login TIMESTAMP;
ALTER TABLE users ADD COLUMN IF NOT EXISTS subscription_start TIMESTAMP;
ALTER TABLE users ADD COLUMN IF NOT EXISTS stripe_subscription_id VARCHAR(255);

-- Fix a specific user's subscription (replace user_id)
UPDATE users 
SET subscription_status = 'active',
    subscription_end = NOW() + INTERVAL '30 days',
    subscription_start = COALESCE(subscription_start, NOW())
WHERE email = 'your-email@example.com';
    """, language="sql")
