import streamlit as st
import psycopg2
import socket
import requests

st.title("Database Connection Test")

# Display IP address information
try:
    # Get hostname
    hostname = socket.gethostname()
    st.write(f"Hostname: {hostname}")
    
    # Get local IP
    local_ip = socket.gethostbyname(hostname)
    st.write(f"Local IP: {local_ip}")
    
    # Try to get public IP
    try:
        public_ip = requests.get('https://api.ipify.org').text
        st.write(f"Public IP: {public_ip}")
    except:
        st.write("Couldn't determine public IP")
    
    st.markdown("---")
except Exception as e:
    st.error(f"Error determining IP: {str(e)}")

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
        
        # Test basic network connectivity before trying the full connection
        st.markdown("---")
        st.subheader("Network Connectivity Test")
        
        try:
            # Check if we can connect to the port
            import socket
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(5)  # 5 second timeout
            
            host = st.secrets["DB_HOST"]
            port = int(st.secrets["DB_PORT"])
            
            st.write(f"Testing if {host}:{port} is reachable...")
            result = s.connect_ex((host, port))
            s.close()
            
            if result == 0:
                st.success(f"✅ Port {port} on host {host} is OPEN and reachable!")
            else:
                st.error(f"❌ Could not connect to {host} on port {port}. Connection failed with error code {result}.")
                st.warning("This indicates a network connectivity issue. Check your firewall settings and make sure your PostgreSQL instance allows connections from your Streamlit app.")
        except Exception as e:
            st.error(f"Error during connectivity test: {str(e)}")
        
        st.markdown("---")
        st.subheader("Database Connection Test")
        
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
            
            # Provide more detailed troubleshooting advice
            st.markdown("### Troubleshooting Tips:")
            st.markdown("""
            1. **Check your DB_NAME**: Make sure it's the actual database name, not a connection name or instance ID
            2. **Verify credentials**: Double-check username and password
            3. **Check IP allowlist**: Make sure your Google Cloud SQL instance allows connections from your app's IP address
            4. **Check network/firewall rules**: Ensure port 5432 is open for connections
            5. **SSL Requirements**: Google Cloud SQL might require SSL connections
            """)
            
            # If it looks like an SSL issue, provide more guidance
            if "SSL" in str(e) or "certificate" in str(e).lower():
                st.markdown("""
                ### SSL Connection Tips:
                
                For Google Cloud SQL, you might need to add SSL parameters to your connection:
                
                ```python
                conn = psycopg2.connect(
                    dbname=st.secrets["DB_NAME"],
                    user=st.secrets["DB_USER"],
                    password=st.secrets["DB_PASSWORD"],
                    host=st.secrets["DB_HOST"],
                    port=st.secrets["DB_PORT"],
                    sslmode='require'
                )
                ```
                
                For even more secure connections, you can use client certificates.
                """)
            
except Exception as e:
    st.error(f"Error accessing secrets: {str(e)}")
