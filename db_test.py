import streamlit as st
import psycopg2

st.title("Database Connection Test")

# Try to access secrets
try:
    st.write("Checking for database secrets...")
    required_secrets = ["DB_NAME", "DB_USER", "DB_PASSWORD", "DB_HOST", "DB_PORT"]
    
    missing_secrets = []
    for secret in required_secrets:
        if secret not in st.secrets:
            missing_secrets.append(secret)
    
    if missing_secrets:
        st.error(f"Missing database secrets: {', '.join(missing_secrets)}")
    else:
        st.success("All required database secrets are present")
        
        # Display the secrets (you may want to mask passwords in production)
        st.write(f"DB Host: {st.secrets['DB_HOST']}")
        st.write(f"DB Port: {st.secrets['DB_PORT']}")
        st.write(f"DB Name: {st.secrets['DB_NAME']}")
        st.write(f"DB User: {st.secrets['DB_USER']}")
        
        # Try to connect
        try:
            st.write("Attempting database connection...")
            conn = psycopg2.connect(
                dbname=st.secrets["DB_NAME"],
                user=st.secrets["DB_USER"],
                password=st.secrets["DB_PASSWORD"],
                host=st.secrets["DB_HOST"],
                port=st.secrets["DB_PORT"]
            )
            
            st.success("✅ Database connection successful!")
            
            # Test a simple query
            with conn.cursor() as cur:
                st.write("Testing a simple query...")
                cur.execute("SELECT version();")
                version = cur.fetchone()
                st.write(f"PostgreSQL version: {version[0]}")
                
            conn.close()
            
        except Exception as e:
            st.error(f"❌ Database connection failed: {str(e)}")
            
except Exception as e:
    st.error(f"Error accessing secrets: {str(e)}")
