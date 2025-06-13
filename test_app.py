import streamlit as st

st.set_page_config(page_title="CareerVertex Test", layout="wide")

st.title("CareerVertex - Test Page")
st.write("If you can see this, Streamlit is working!")

# Test secrets
st.subheader("Configuration Check")

# Check for database secrets
db_secrets = ["DB_HOST", "DB_PORT", "DB_NAME", "DB_USER", "DB_PASSWORD"]
missing_db = []
for secret in db_secrets:
    if secret in st.secrets:
        st.success(f"✓ {secret} is configured")
    else:
        st.error(f"✗ {secret} is missing")
        missing_db.append(secret)

# Check for other required secrets
other_secrets = ["ANTHROPIC_API_KEY", "STRIPE_SECRET_KEY", "STRIPE_PRICE_ID", "APP_URL"]
missing_other = []
for secret in other_secrets:
    if secret in st.secrets:
        st.success(f"✓ {secret} is configured")
    else:
        st.warning(f"✗ {secret} is missing")
        missing_other.append(secret)

# Test database connection if all DB secrets present
if not missing_db:
    st.subheader("Database Connection Test")
    try:
        import psycopg2
        conn = psycopg2.connect(
            dbname=st.secrets["DB_NAME"],
            user=st.secrets["DB_USER"],
            password=st.secrets["DB_PASSWORD"],
            host=st.secrets["DB_HOST"],
            port=st.secrets["DB_PORT"],
            sslmode='require'
        )
        st.success("✓ Database connection successful!")
        conn.close()
    except Exception as e:
        st.error(f"✗ Database connection failed: {e}")

# Test module imports
st.subheader("Module Import Test")
modules_to_test = [
    "psycopg2",
    "bcrypt",
    "anthropic",
    "stripe",
    "PyPDF2",
    "docx"
]

for module in modules_to_test:
    try:
        __import__(module)
        st.success(f"✓ {module} imported successfully")
    except ImportError:
        st.error(f"✗ Failed to import {module}")

# Show Python version
import sys
st.info(f"Python version: {sys.version}")

# Show current directory structure
import os
st.subheader("Application Structure")
st.write("Current directory:", os.getcwd())
st.write("Files in current directory:", os.listdir('.'))

# Check for required directories
required_dirs = ['core', 'pages', 'components', 'utils', 'static']
for dir_name in required_dirs:
    if os.path.exists(dir_name):
        st.success(f"✓ {dir_name}/ directory exists")
        # List files in directory
        files = os.listdir(dir_name)
        if files:
            st.write(f"  Files: {', '.join(files)}")
    else:
        st.error(f"✗ {dir_name}/ directory missing")
