import streamlit as st

st.write("Starting app initialization...")

import pandas as pd
import altair as alt
import numpy as np
import io
import json
import time
import traceback
import hmac
import re
import os
import uuid
import hashlib
from datetime import datetime, timedelta
from functools import lru_cache
from PyPDF2 import PdfReader
import docx
import anthropic
import stripe
import psycopg2
from psycopg2.extras import Json, DictCursor
from psycopg2 import pool
import bcrypt

# === APP CONFIGURATION ===
st.set_page_config(
    page_title="CareerVertex - CV Job Match Analyser",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# === THEME SETTINGS AND CUSTOM CSS ===
custom_css = """
:root {
    --primary-color: #4169E1;
    --secondary-color: #6c757d;
    --background-color: #f8f9fa;
    --surface-color: #ffffff;
    --text-color: #212529;
    --light-accent: #e9ecef;
    --mid-accent: #dee2e6;
    --dark-accent: #adb5bd;
    --card-shadow: rgba(0, 0, 0, 0.1);
    --tag-bg: #e9ecef;
    --strength-color: #28a745;
    --improve-color: #fd7e14;
    --score-high: #28a745;
    --score-mid: #fd7e14;
    --score-low: #dc3545;
}

.stApp {
    background-color: var(--background-color);
    color: var(--text-color);
}

.stTabs [data-baseweb="tab-list"] {
    gap: 2px;
}

.stTabs [data-baseweb="tab"] {
    background-color: var(--surface-color);
    color: var(--text-color);
    border-radius: 4px 4px 0 0;
}

.stTabs [aria-selected="true"] {
    background-color: var(--primary-color) !important;
    color: white !important;
}

div.card {
    border-radius: 10px;
    background-color: var(--surface-color);
    padding: 1.5rem;
    margin-bottom: 1rem;
    box-shadow: 0 4px 6px var(--card-shadow);
}

div.keyword-tag {
    display: inline-block;
    background-color: var(--tag-bg);
    border-radius: 20px;
    padding: 8px 16px;
    margin: 5px;
    font-weight: 500;
    text-align: center;
}

div.trend-card {
    background-color: var(--surface-color);
    padding: 15px;
    margin: 10px 0;
    border-left: 4px solid var(--primary-color);
    border-radius: 5px;
}

.match-score-high {
    color: var(--score-high);
    font-size: 3.5rem;
    font-weight: bold;
}

.match-score-mid {
    color: var(--score-mid);
    font-size: 3.5rem;
    font-weight: bold;
}

.match-score-low {
    color: var(--score-low);
    font-size: 3.5rem;
    font-weight: bold;
}

.strength-item {
    color: var(--strength-color);
    margin-bottom: 0.5rem;
}

.improvement-item {
    color: var(--improve-color);
    margin-bottom: 0.5rem;
}

/* Enhancing form inputs */
div[data-baseweb="input"] input, 
div[data-baseweb="textarea"] textarea {
    background-color: var(--surface-color);
    color: var(--text-color);
    border: 1px solid var(--mid-accent);
}

/* Button styling */
.stButton button {
    border-radius: 6px;
}

.stButton > button[data-baseweb="button"] {
    border: 1px solid var(--mid-accent);
}

/* Pricing card styling */
.pricing-card {
    border: 1px solid var(--mid-accent);
    border-radius: 10px;
    padding: 20px;
    text-align: center;
    background-color: var(--surface-color);
    box-shadow: 0 4px 6px var(--card-shadow);
    height: 100%;
}

.pricing-card h3 {
    color: var(--primary-color);
    margin-bottom: 15px;
}

.pricing-price {
    font-size: 2rem;
    font-weight: bold;
    margin: 15px 0;
}

.pricing-period {
    font-size: 0.9rem;
    opacity: 0.8;
}

.feature-item {
    margin: 8px 0;
    text-align: left;
}

.feature-item i {
    color: var(--primary-color);
    margin-right: 5px;
}

/* Subscription badge */
.subscription-badge {
    display: inline-block;
    background-color: var(--primary-color);
    color: white;
    padding: 5px 10px;
    border-radius: 15px;
    font-size: 0.8rem;
    font-weight: bold;
}

.subscription-badge.expired {
    background-color: var(--score-low);
}

/* User profile card */
.user-profile {
    border-radius: 10px;
    padding: 15px;
    background-color: var(--surface-color);
    margin-bottom: 15px;
}

.user-avatar {
    width: 50px;
    height: 50px;
    border-radius: 25px;
    background-color: var(--primary-color);
    color: white;
    display: flex;
    align-items: center;
    justify-content: center;
    font-weight: bold;
    font-size: 1.2rem;
    margin-right: 15px;
}
"""

st.markdown(f"""
<style>{custom_css}</style>
""", unsafe_allow_html=True)

# === ERROR TRACKING SYSTEM ===
ERROR_MESSAGES = {
    "api_timeout": "The API request timed out. This could be due to high server load or a complex CV. Please try again.",
    "api_error": "There was an error communicating with the AI service. Please try again later.",
    "parse_error": "There was an error parsing your document. Please check file format and try again.",
    "json_error": "There was an error processing the response data. Please try again.",
    "db_error": "There was a database error. Please try again later.",
    "auth_error": "Authentication error. Please check your credentials and try again.",
    "payment_error": "There was an error processing your payment. Please try again."
}

class ErrorTracker:
    """Tracks and manages errors throughout the application."""
    
    def __init__(self):
        self.errors = []
        self.has_critical_error = False
    
    def add_error(self, error_type, message, critical=False, details=None):
        """Add an error to the tracking system"""
        timestamp = datetime.now().isoformat()
        error = {
            "timestamp": timestamp,
            "type": error_type,
            "message": message,
            "critical": critical,
            "details": details
        }
        self.errors.append(error)
        
        if critical:
            self.has_critical_error = True
            # Log critical errors for monitoring
            print(f"CRITICAL ERROR: {error_type} - {message}")
            if details:
                print(f"Details: {details}")
    
    def get_user_message(self, error_type):
        """Get a user-friendly error message"""
        return ERROR_MESSAGES.get(error_type, "An unexpected error occurred. Please try again.")
    
    def display_errors(self):
        """Display errors in the Streamlit UI if they exist"""
        if not self.errors:
            return
        
        with st.expander("Troubleshooting Information", expanded=self.has_critical_error):
            for error in self.errors:
                if error["critical"]:
                    st.error(f"{error['message']}")
                else:
                    st.warning(f"{error['message']}")
                
                if error.get("details") and st.checkbox("Show technical details"):
                    st.code(error["details"])
            
            if self.has_critical_error:
                st.info("If this problem persists, try uploading a different file format or simplify your CV.")

# Global error tracker instance
error_tracker = ErrorTracker()

# === DATABASE CONNECTION MANAGEMENT ===
class DatabaseManager:
    """Manages database connections and operations."""
    
    def __init__(self):
        self.conn_pool = None
        
        # Initialize connection pool
        try:
            # Check for required secrets
            required_db_secrets = ["DB_NAME", "DB_USER", "DB_PASSWORD", "DB_HOST", "DB_PORT"]
            for secret in required_db_secrets:
                if secret not in st.secrets:
                    st.error(f"Missing required database secret: {secret}")
                    print(f"Missing required database secret: {secret}")
                    return

            # Connect to Google Cloud SQL PostgreSQL
            self.conn_pool = psycopg2.pool.SimpleConnectionPool(
                1, 10,
                dbname=st.secrets["DB_NAME"],
                user=st.secrets["DB_USER"],
                password=st.secrets["DB_PASSWORD"],
                host=st.secrets["DB_HOST"],
                port=st.secrets["DB_PORT"],
                # Uncomment if using SSL (often required for Google Cloud SQL)
                sslmode='require',
                # Add these if you're using SSL certificates
                # sslrootcert=st.secrets.get("DB_SSL_ROOT_CERT"),
                # sslcert=st.secrets.get("DB_SSL_CERT"),
                # sslkey=st.secrets.get("DB_SSL_KEY"),
            )
            print("Database connection pool initialized to Google Cloud SQL")
            st.success("✅ Connected to Google Cloud SQL database")
        except Exception as e:
            error_tracker.add_error("db_error", "Failed to initialize database connection pool", True, str(e))
            st.error(f"❌ Database connection failed: {str(e)}")
            print(f"Database connection error: {str(e)}")
            self.conn_pool = None
    
    def get_connection(self):
        """Get a connection from the pool."""
        if not self.conn_pool:
            error_tracker.add_error("db_error", "No database connection pool available", True)
            return None
            
        try:
            return self.conn_pool.getconn()
        except Exception as e:
            error_tracker.add_error("db_error", "Failed to get database connection", True, str(e))
            return None
    
    def release_connection(self, conn):
        """Release a connection back to the pool."""
        if self.conn_pool and conn:
            try:
                self.conn_pool.putconn(conn)
            except Exception as e:
                error_tracker.add_error("db_error", "Failed to release database connection", False, str(e))
    
    def execute_query(self, query, params=None, fetch=True, commit=True):
        """Execute a database query with proper connection management."""
        conn = None
        result = None
        try:
            conn = self.get_connection()
            if not conn:
                return None
                
            with conn.cursor(cursor_factory=DictCursor) as cur:
                cur.execute(query, params)
                
                if fetch:
                    result = cur.fetchall()
                    
                if commit:
                    conn.commit()
                    
                return result
        except Exception as e:
            if conn:
                conn.rollback()
            error_tracker.add_error("db_error", "Database query execution failed", True, str(e))
            return None
        finally:
            if conn:
                self.release_connection(conn)
    
    def initialize_schema(self):
        """Initialize the database schema if it doesn't exist."""
        schema_queries = [
            """
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
            """,
            """
            CREATE TABLE IF NOT EXISTS payments (
                payment_id UUID PRIMARY KEY,
                user_id UUID REFERENCES users(user_id),
                amount DECIMAL(10, 2) NOT NULL,
                currency VARCHAR(3) NOT NULL,
                payment_date TIMESTAMP DEFAULT NOW(),
                payment_method VARCHAR(50),
                stripe_payment_id VARCHAR(255),
                status VARCHAR(50)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS cvs (
                cv_id UUID PRIMARY KEY,
                user_id UUID REFERENCES users(user_id),
                cv_name VARCHAR(255) NOT NULL,
                cv_text TEXT,
                upload_date TIMESTAMP DEFAULT NOW(),
                parsed_data JSONB
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS job_descriptions (
                job_description_id UUID PRIMARY KEY,
                user_id UUID REFERENCES users(user_id),
                job_title VARCHAR(255),
                company VARCHAR(255),
                description_text TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT NOW()
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS analyses (
                analysis_id UUID PRIMARY KEY,
                user_id UUID REFERENCES users(user_id),
                cv_id UUID REFERENCES cvs(cv_id),
                job_description_id UUID REFERENCES job_descriptions(job_description_id),
                match_score INTEGER,
                analysis_data JSONB,
                created_at TIMESTAMP DEFAULT NOW()
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS token_usage (
                usage_id UUID PRIMARY KEY,
                user_id UUID REFERENCES users(user_id),
                request_type VARCHAR(50) NOT NULL,
                tokens_used INTEGER NOT NULL,
                request_date TIMESTAMP DEFAULT NOW()
            )
            """
        ]
        
        for query in schema_queries:
            self.execute_query(query, fetch=False)
            
        print("Database schema initialized")

# Initialize database manager
db_manager = DatabaseManager()

# Make sure schema is initialized
db_manager.initialize_schema()

# === STRIPE INTEGRATION ===
# Initialize Stripe with API key
stripe.api_key = st.secrets["STRIPE_SECRET_KEY"]

def create_stripe_checkout_session(user_id, email):
    """Create a Stripe checkout session for subscription."""
    try:
        checkout_session = stripe.checkout.Session.create(
            customer_email=email,
            payment_method_types=["card"],
            line_items=[
                {
                    "price": st.secrets["STRIPE_PRICE_ID"],  # Monthly subscription price ID
                    "quantity": 1,
                },
            ],
            mode="subscription",
            success_url=st.secrets["APP_URL"] + "?success=true&session_id={CHECKOUT_SESSION_ID}",
            cancel_url=st.secrets["APP_URL"] + "?canceled=true",
            client_reference_id=str(user_id),
            metadata={"user_id": str(user_id)}
        )
        return checkout_session
    except Exception as e:
        error_tracker.add_error("payment_error", "Failed to create checkout session", True, str(e))
        return None

def handle_successful_payment(session_id):
    """Process a successful payment."""
    try:
        # Get the checkout session
        checkout_session = stripe.checkout.Session.retrieve(session_id)
        
        # Get customer details
        user_id = checkout_session.metadata.get("user_id")
        if not user_id:
            return False
            
        # Get subscription details
        subscription = stripe.Subscription.retrieve(checkout_session.subscription)
        
        # Calculate subscription end date (30 days from now)
        subscription_start = datetime.fromtimestamp(subscription.current_period_start)
        subscription_end = datetime.fromtimestamp(subscription.current_period_end)
        
        # Update user subscription in database
        db_manager.execute_query(
            """
            UPDATE users 
            SET subscription_status = %s, 
                subscription_start = %s,
                subscription_end = %s,
                stripe_customer_id = %s,
                stripe_subscription_id = %s
            WHERE user_id = %s
            """,
            (
                'active',
                subscription_start,
                subscription_end,
                checkout_session.customer,
                subscription.id,
                user_id
            ),
            fetch=False
        )
        
        # Record the payment
        payment_id = uuid.uuid4()
        db_manager.execute_query(
            """
            INSERT INTO payments (
                payment_id, user_id, amount, currency, 
                payment_method, stripe_payment_id, status
            ) VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            (
                payment_id,
                user_id,
                float(subscription.plan.amount) / 100,  # Convert from pence to pounds
                subscription.plan.currency.upper(),
                "card",
                checkout_session.payment_intent,
                "completed"
            ),
            fetch=False
        )
        
        return True
    except Exception as e:
        error_tracker.add_error("payment_error", "Failed to process successful payment", True, str(e))
        return False

# === USER AUTHENTICATION SYSTEM ===
class AuthManager:
    """Manages user authentication and registration."""
    
    def register_user(self, email, password, full_name):
        """Register a new user."""
        try:
            # Check if user already exists
            existing_user = db_manager.execute_query(
                "SELECT * FROM users WHERE email = %s",
                (email,)
            )
            
            if existing_user:
                return False, "User with this email already exists."
                
            # Hash the password
            password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            
            # Generate user ID
            user_id = uuid.uuid4()
            
            # Insert user into database
            db_manager.execute_query(
                """
                INSERT INTO users (user_id, email, password_hash, full_name, created_at)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (user_id, email, password_hash, full_name, datetime.now()),
                fetch=False
            )
            
            return True, str(user_id)
        except Exception as e:
            error_tracker.add_error("auth_error", "Failed to register user", True, str(e))
            return False, "Registration failed. Please try again."
    
    def login_user(self, email, password):
        """Login a user and return user data if successful."""
        try:
            # Fetch user from database
            user_data = db_manager.execute_query(
                "SELECT * FROM users WHERE email = %s",
                (email,)
            )
            
            if not user_data:
                return False, "User not found."
                
            user = user_data[0]
            
            # Check password
            if not bcrypt.checkpw(password.encode('utf-8'), user['password_hash'].encode('utf-8')):
                return False, "Incorrect password."
                
            # Update last login time
            db_manager.execute_query(
                "UPDATE users SET last_login = %s WHERE user_id = %s",
                (datetime.now(), user['user_id']),
                fetch=False
            )
            
            # Return user data
            return True, dict(user)
        except Exception as e:
            error_tracker.add_error("auth_error", "Failed to login user", True, str(e))
            return False, "Login failed. Please try again."
    
    def check_admin_password(self):
        """Returns `True` if the admin credentials are correct."""
        def login_form():
            """Form with widgets to collect admin credentials"""
            with st.form("Admin Credentials"):
                st.text_input("Username", key="admin_username")
                st.text_input("Password", type="password", key="admin_password")
                st.form_submit_button("Log in", on_click=admin_password_entered)

        def admin_password_entered():
            """Checks whether admin password is correct."""
            # Ensure secrets and passwords structure exists before accessing
            if "admin_passwords" in st.secrets and st.session_state["admin_username"] in st.secrets["admin_passwords"]:
                stored_password = st.secrets.admin_passwords[st.session_state["admin_username"]]
                # Ensure stored_password is a string or bytes for hmac.compare_digest
                if isinstance(stored_password, (str, bytes)):
                     if hmac.compare_digest(
                        st.session_state["admin_password"],
                        str(stored_password) # Ensure it's compared as string if needed
                     ):
                        st.session_state["admin_password_correct"] = True
                        del st.session_state["admin_password"]  # Don't store the username or password.
                        del st.session_state["admin_username"]
                        return # Exit function on success
                else:
                     st.error(f"Password configuration error for admin user {st.session_state['admin_username']}.")

            # If checks failed or structure doesn't exist
            st.session_state["admin_password_correct"] = False

        # Return True if the username + password is validated.
        if st.session_state.get("admin_password_correct", False):
            return True

        # Show inputs for username + password.
        login_form()
        if "admin_password_correct" in st.session_state and not st.session_state["admin_password_correct"]:
            st.error("😕 Admin user not known or password incorrect")
        return False
    
    def check_subscription(self, user_id):
        """Check if user has an active subscription."""
        try:
            user_data = db_manager.execute_query(
                """
                SELECT subscription_status, subscription_end 
                FROM users 
                WHERE user_id = %s
                """,
                (user_id,)
            )
            
            if not user_data:
                return False
                
            user = user_data[0]
            
            # Check if subscription is active and not expired
            if user['subscription_status'] == 'active' and user['subscription_end'] > datetime.now():
                return True
            else:
                # Update status to expired if past end date
                if user['subscription_status'] == 'active' and user['subscription_end'] <= datetime.now():
                    db_manager.execute_query(
                        "UPDATE users SET subscription_status = 'expired' WHERE user_id = %s",
                        (user_id,),
                        fetch=False
                    )
                return False
        except Exception as e:
            error_tracker.add_error("auth_error", "Failed to check subscription", False, str(e))
            return False
    
    def get_user_data(self, user_id):
        """Get user data by ID."""
        try:
            user_data = db_manager.execute_query(
                "SELECT * FROM users WHERE user_id = %s",
                (user_id,)
            )
            
            if not user_data:
                return None
                
            return dict(user_data[0])
        except Exception as e:
            error_tracker.add_error("auth_error", "Failed to get user data", False, str(e))
            return None
    
    def logout_user(self):
        """Logout the current user."""
        for key in ['user_id', 'user_email', 'user_name', 'user_data']:
            if key in st.session_state:
                del st.session_state[key]

# Initialize auth manager
auth_manager = AuthManager()

# === TEXT EXTRACTION UTILITIES ===
def extract_text_from_pdf(file):
    """Extract text from a PDF file."""
    try:
        reader = PdfReader(file)
        text = ""
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                 text += page_text + "\n"
        return text
    except Exception as e:
        error_tracker.add_error("parse_error", f"Error reading PDF {file.name}", True, str(e))
        return ""

def extract_text_from_docx(file):
    """Extract text from a DOCX file."""
    try:
        doc = docx.Document(file)
        text = ""
        for para in doc.paragraphs:
            text += para.text + "\n"
        return text
    except Exception as e:
        error_tracker.add_error("parse_error", f"Error reading DOCX {file.name}", True, str(e))
        return ""

def extract_text_from_file(file):
    """Extract text from a supported file format (PDF, DOCX, TXT)."""
    file_name = file.name.lower()
    # Read content once
    try:
        file_content = file.read()
        # Reset file pointer AFTER reading
        file.seek(0)
    except Exception as e:
        error_tracker.add_error("parse_error", f"Error reading file {file.name}", True, str(e))
        return None

    if file_name.endswith('.pdf'):
        return extract_text_from_pdf(file)
    elif file_name.endswith('.docx'):
        # Use BytesIO for docx
        return extract_text_from_docx(io.BytesIO(file_content))
    elif file_name.endswith('.txt'):
        # Decode bytes to string with error handling
        try:
            return file_content.decode('utf-8')
        except UnicodeDecodeError:
            try:
                # Try another common encoding
                return file_content.decode('latin-1')
            except Exception as e:
                error_tracker.add_error("parse_error", f"Error decoding text file {file.name}", True, str(e))
                return None
    else:
        error_tracker.add_error("parse_error", f"Unsupported file type: {file_name}", False)
        return None

# === JSON PARSING UTILITIES ===
def extract_json_from_string(text, default_structure=None):
    """
    Extracts JSON object from a string with multiple fallback strategies.
    Returns extracted JSON string or default_structure if all extraction methods fail.
    """
    if not text:
        error_tracker.add_error("parse_error", "Empty response received from API.", True)
        return default_structure
    
    # Strategy 1: Look for JSON within ```json ... ``` markdown fences
    json_pattern = r'```(?:json)?\s*(\{.*\}|\[.*\])\s*```'
    match = re.search(json_pattern, text, re.DOTALL | re.IGNORECASE)
    if match:
        potential_json = match.group(1).strip()
        try:
            # Validate by parsing and re-stringifying to ensure valid JSON
            parsed = json.loads(potential_json)
            return json.dumps(parsed)  # Return validated and normalized JSON string
        except json.JSONDecodeError:
            # If parsing fails, continue to next strategy
            pass
    
    # Strategy 2: Find outermost matching braces/brackets - more careful approach
    # First check if entire text is valid JSON
    try:
        parsed = json.loads(text.strip())
        return json.dumps(parsed)  # Return validated JSON
    except json.JSONDecodeError:
        pass
        
    # Strategy 3: Find the first occurrence of what looks like a JSON object/array
    # This is riskier, so we do it later
    bracket_pattern = r'(\{.*\}|\[.*\])'
    match = re.search(bracket_pattern, text, re.DOTALL)
    if match:
        potential_json = match.group(0).strip()
        try:
            parsed = json.loads(potential_json)
            return json.dumps(parsed)  # Return validated JSON
        except json.JSONDecodeError:
            pass
    
    # Strategy 4: As a last resort, try to clean up the text by removing common issues
    cleaned_text = text.strip()
    # Try to find the first { or [ and the last } or ]
    start_brace = cleaned_text.find('{')
    start_bracket = cleaned_text.find('[')
    end_brace = cleaned_text.rfind('}')
    end_bracket = cleaned_text.rfind(']')
    
    # Determine which kind of structure we're dealing with (if any)
    if start_brace >= 0 and end_brace >= 0 and (start_bracket < 0 or start_brace < start_bracket):
        potential_json = cleaned_text[start_brace:end_brace+1]
    elif start_bracket >= 0 and end_bracket >= 0:
        potential_json = cleaned_text[start_bracket:end_bracket+1]
    else:
        # No valid JSON structure found
        error_tracker.add_error("json_error", "Could not find a valid JSON structure in the response.", True)
        if default_structure is not None:
            st.info("Using fallback structure instead.")
        return default_structure
    
    try:
        parsed = json.loads(potential_json)
        return json.dumps(parsed)  # Return validated JSON
    except json.JSONDecodeError:
        # All strategies failed
        error_tracker.add_error("json_error", "All JSON extraction strategies failed. The response is not valid JSON.", True)
        if default_structure is not None:
            st.info("Using fallback structure instead.")
        return default_structure

# === API CLIENT UTILITIES ===
def call_anthropic_api_with_timeout(client, prompt, model="claude-3-5-sonnet-20240620", 
                                   max_tokens=2000, temperature=0.0, system="", 
                                   timeout=60, retries=2):
    """
    Makes an API call to Anthropic with timeout handling and retries.
    """
    start_time = time.time()
    current_attempt = 0
    
    while current_attempt <= retries:
        current_attempt += 1
        try:
            # Create a timeout context
            response = client.messages.create(
                model=model,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system,
                messages=[{"role": "user", "content": prompt}],
                timeout=timeout  # Will raise exception if call takes too long
            )
            
            if response and hasattr(response, 'content') and len(response.content) > 0:
                # Calculate token usage and log it if user_id is available
                if 'user_id' in st.session_state:
                    tokens_used = response.usage.input_tokens + response.usage.output_tokens
                    log_token_usage(st.session_state['user_id'], "cv_analysis", tokens_used)
                    
                return True, response.content[0].text
            else:
                return False, "Empty response received from API"
                
        except anthropic.APITimeoutError:
            if current_attempt <= retries:
                remaining_time = timeout - (time.time() - start_time)
                if remaining_time > 0:
                    st.warning(f"API timeout. Retrying... (Attempt {current_attempt}/{retries})")
                    time.sleep(min(3, remaining_time))  # Brief pause before retry
                else:
                    error_tracker.add_error("api_timeout", f"Timeout after {timeout} seconds. The request took too long to complete.", True)
                    return False, f"Timeout after {timeout} seconds. The request took too long to complete."
            else:
                error_tracker.add_error("api_timeout", f"Request timed out after {timeout} seconds and {retries} retries.", True)
                return False, f"Request timed out after {timeout} seconds and {retries} retries."
        except anthropic.APIConnectionError as e:
            error_tracker.add_error("api_error", "Connection error when calling AI service", True, str(e))
            return False, f"Connection error: {str(e)}"
        except anthropic.APIError as e:
            error_tracker.add_error("api_error", "API error from AI service", True, str(e))
            return False, f"API error: {str(e)}"
        except anthropic.RateLimitError as e:
            error_tracker.add_error("api_error", "Rate limit exceeded when calling AI service", True, str(e))
            return False, f"Rate limit exceeded: {str(e)}"
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            error_tracker.add_error("api_error", "Unexpected error when calling AI service", True, traceback.format_exc())
            return False, error_msg
    
    return False, "Maximum retries exceeded with no successful response."

def initialize_anthropic_client():
    """Initialize the Anthropic client with proper error handling."""
    try:
        # Use anthropic.Anthropic for newer versions
        client = anthropic.Anthropic(api_key=st.secrets["ANTHROPIC_API_KEY"])
        return client
    except AttributeError:
        # Fallback for older versions if needed
        client = anthropic.Client(api_key=st.secrets["ANTHROPIC_API_KEY"])
        return client
    except KeyError:
        st.error("ANTHROPIC_API_KEY not found in Streamlit secrets. Please add it to your .streamlit/secrets.toml file.")
        st.info("To learn how to set up Streamlit secrets, visit: https://docs.streamlit.io/library/advanced-features/secrets-management")
        return None

def log_token_usage(user_id, request_type, tokens_used):
    """Log token usage to the database."""
    try:
        usage_id = uuid.uuid4()
        db_manager.execute_query(
            """
            INSERT INTO token_usage (usage_id, user_id, request_type, tokens_used)
            VALUES (%s, %s, %s, %s)
            """,
            (usage_id, user_id, request_type, tokens_used),
            fetch=False
        )
        return True
    except Exception as e:
        error_tracker.add_error("db_error", "Failed to log token usage", False, str(e))
        return False

# === CV AND JOB DESCRIPTION MANAGEMENT ===
def save_cv(user_id, cv_name, cv_text):
    """Save a CV to the database."""
    try:
        # Check if user already has a CV with this name
        existing_cv = db_manager.execute_query(
            "SELECT * FROM cvs WHERE user_id = %s AND cv_name = %s",
            (user_id, cv_name)
        )
        
        if existing_cv:
            # Update existing CV
            db_manager.execute_query(
                """
                UPDATE cvs 
                SET cv_text = %s, upload_date = %s, parsed_data = NULL
                WHERE user_id = %s AND cv_name = %s
                """,
                (cv_text, datetime.now(), user_id, cv_name),
                fetch=False
            )
            return True, existing_cv[0]['cv_id']
        else:
            # Create new CV
            cv_id = uuid.uuid4()
            db_manager.execute_query(
                """
                INSERT INTO cvs (cv_id, user_id, cv_name, cv_text, upload_date)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (cv_id, user_id, cv_name, cv_text, datetime.now()),
                fetch=False
            )
            return True, cv_id
    except Exception as e:
        error_tracker.add_error("db_error", "Failed to save CV", True, str(e))
        return False, None

def get_user_cvs(user_id):
    """Get all CVs for a user."""
    try:
        cvs = db_manager.execute_query(
            "SELECT * FROM cvs WHERE user_id = %s ORDER BY upload_date DESC",
            (user_id,)
        )
        
        if not cvs:
            return []
            
        return [dict(cv) for cv in cvs]
    except Exception as e:
        error_tracker.add_error("db_error", "Failed to get user CVs", False, str(e))
        return []

def get_cv_by_id(cv_id):
    """Get a CV by ID."""
    try:
        cv_data = db_manager.execute_query(
            "SELECT * FROM cvs WHERE cv_id = %s",
            (cv_id,)
        )
        
        if not cv_data:
            return None
            
        return dict(cv_data[0])
    except Exception as e:
        error_tracker.add_error("db_error", "Failed to get CV by ID", False, str(e))
        return None

def save_job_description(user_id, job_title, company, description_text):
    """Save a job description to the database."""
    try:
        job_description_id = uuid.uuid4()
        db_manager.execute_query(
            """
            INSERT INTO job_descriptions 
            (job_description_id, user_id, job_title, company, description_text)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (job_description_id, user_id, job_title, company, description_text),
            fetch=False
        )
        return True, job_description_id
    except Exception as e:
        error_tracker.add_error("db_error", "Failed to save job description", True, str(e))
        return False, None

def get_user_job_descriptions(user_id):
    """Get all job descriptions for a user."""
    try:
        job_descriptions = db_manager.execute_query(
            "SELECT * FROM job_descriptions WHERE user_id = %s ORDER BY created_at DESC",
            (user_id,)
        )
        
        if not job_descriptions:
            return []
            
        return [dict(jd) for jd in job_descriptions]
    except Exception as e:
        error_tracker.add_error("db_error", "Failed to get user job descriptions", False, str(e))
        return []

def get_job_description_by_id(job_description_id):
    """Get a job description by ID."""
    try:
        jd_data = db_manager.execute_query(
            "SELECT * FROM job_descriptions WHERE job_description_id = %s",
            (job_description_id,)
        )
        
        if not jd_data:
            return None
            
        return dict(jd_data[0])
    except Exception as e:
        error_tracker.add_error("db_error", "Failed to get job description by ID", False, str(e))
        return None

def save_analysis_result(user_id, cv_id, job_description_id, match_score, analysis_data):
    """Save analysis result to the database."""
    try:
        analysis_id = uuid.uuid4()
        db_manager.execute_query(
            """
            INSERT INTO analyses 
            (analysis_id, user_id, cv_id, job_description_id, match_score, analysis_data)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (analysis_id, user_id, cv_id, job_description_id, match_score, Json(analysis_data)),
            fetch=False
        )
        return True, analysis_id
    except Exception as e:
        error_tracker.add_error("db_error", "Failed to save analysis result", True, str(e))
        return False, None

def get_user_analyses(user_id):
    """Get all analyses for a user."""
    try:
        analyses = db_manager.execute_query(
            """
            SELECT a.*, c.cv_name, j.job_title, j.company
            FROM analyses a
            JOIN cvs c ON a.cv_id = c.cv_id
            JOIN job_descriptions j ON a.job_description_id = j.job_description_id
            WHERE a.user_id = %s
            ORDER BY a.created_at DESC
            """,
            (user_id,)
        )
        
        if not analyses:
            return []
            
        return [dict(analysis) for analysis in analyses]
    except Exception as e:
        error_tracker.add_error("db_error", "Failed to get user analyses", False, str(e))
        return []

def get_analysis_by_id(analysis_id):
    """Get an analysis by ID."""
    try:
        analysis_data = db_manager.execute_query(
            """
            SELECT a.*, c.cv_name, c.cv_text, c.parsed_data as cv_parsed_data,
                   j.job_title, j.company, j.description_text
            FROM analyses a
            JOIN cvs c ON a.cv_id = c.cv_id
            JOIN job_descriptions j ON a.job_description_id = j.job_description_id
            WHERE a.analysis_id = %s
            """,
            (analysis_id,)
        )
        
        if not analysis_data:
            return None
            
        return dict(analysis_data[0])
    except Exception as e:
        error_tracker.add_error("db_error", "Failed to get analysis by ID", False, str(e))
        return None

def update_cv_parsed_data(cv_id, parsed_data):
    """Update the parsed data for a CV."""
    try:
        db_manager.execute_query(
            "UPDATE cvs SET parsed_data = %s WHERE cv_id = %s",
            (Json(parsed_data), cv_id),
            fetch=False
        )
        return True
    except Exception as e:
        error_tracker.add_error("db_error", "Failed to update CV parsed data", False, str(e))
        return False

# === UI COMPONENTS ===
def create_skills_chart(skills_assessment):
    """Create a horizontal bar chart for skills assessment."""
    if not skills_assessment:
        return None
        
    # Create skill rating data for chart
    skill_data = []
    for skill, rating in skills_assessment.items():
        skill_data.append({"Category": skill, "Rating": rating})
        
    if not skill_data:
        return None
        
    skill_df = pd.DataFrame(skill_data)
    
    # Create horizontal bar chart with improved styling
    chart = alt.Chart(skill_df).mark_bar().encode(
        x=alt.X('Rating:Q', scale=alt.Scale(domain=[0, 100]), title='Rating (0-100)'),
        y=alt.Y('Category:N', sort='-x', title=None),
        color=alt.Color('Rating:Q', scale=alt.Scale(scheme='viridis')),
        tooltip=['Category', 'Rating']
    ).properties(height=200)
    
    return chart

def display_match_score(score):
    """Display the match score with appropriate color and text."""
    if score >= 80:
        score_class = "match-score-high"
        score_text = "Strong Match!"
    elif score >= 60:
        score_class = "match-score-mid"
        score_text = "Good Match"
    else:
        score_class = "match-score-low"
        score_text = "Needs Improvement"
        
    # Display overall score with a gauge-like visualization
    st.markdown(f'<div class="{score_class}">{score}%</div>', unsafe_allow_html=True)
    st.markdown(f"### {score_text}")

def display_strengths_and_improvements(strengths, improvements):
    """Display strengths and improvements in a two-column layout."""
    st.markdown('<div class="card">', unsafe_allow_html=True)
    strengths_col, improve_col = st.columns(2)
    
    with strengths_col:
        st.subheader("Your Strengths")
        if strengths:
            for strength in strengths:
                st.markdown(f'<div class="strength-item">✅ {strength}</div>', unsafe_allow_html=True)
        else:
            st.markdown("*No specific strengths identified.*")
            
    with improve_col:
        st.subheader("Areas for Improvement")
        if improvements:
            for area in improvements:
                st.markdown(f'<div class="improvement-item">🔍 {area}</div>', unsafe_allow_html=True)
        else:
            st.markdown("*No specific improvement areas identified.*")
    
    st.markdown('</div>', unsafe_allow_html=True)

def display_recommendations(recommendations):
    """Display recommendations with numbered points."""
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("Recommendations to Improve Your Application")
    if recommendations:
        for i, rec in enumerate(recommendations):
            st.markdown(f"**{i+1}. {rec}**")
    else:
        st.markdown("*No specific recommendations available.*")
    st.markdown('</div>', unsafe_allow_html=True)

def display_keywords(keywords, max_cols=3):
    """Display keywords in a visually appealing grid."""
    st.subheader("Missing Keywords")
    st.markdown("*These keywords appear in the job description but are missing or underemphasised in your CV:*")
    
    if keywords and isinstance(keywords, list):
        # Display keywords as a more visually appealing grid
        keyword_cols = st.columns(max_cols)
        for i, keyword in enumerate(keywords):
            col_idx = i % max_cols
            keyword_cols[col_idx].markdown(
                f'<div class="keyword-tag">{keyword}</div>', 
                unsafe_allow_html=True
            )
    else:
        st.markdown("*No missing keywords identified.*")

def display_trends(trends, max_cols=2):
    """Display industry trends with a nice UI."""
    if trends:
        trend_cols = st.columns(max_cols)
        for i, trend in enumerate(trends):
            col_idx = i % max_cols
            trend_cols[col_idx].markdown(
                f'<div class="trend-card">📈 {trend}</div>', 
                unsafe_allow_html=True
            )
    else:
        st.markdown("*No industry trends identified.*")

def display_cv_summary(cv_data):
    """Display a summary of the parsed CV."""
    if cv_data and 'parsed_data' in cv_data and cv_data['parsed_data']:
        parsed_data = cv_data['parsed_data']
        st.markdown('<div class="card">', unsafe_allow_html=True)
        # Name and contact
        st.markdown(f"### {parsed_data.get('name', 'Candidate')}")
        contact = parsed_data.get('contact_info', {})
        if contact:
            contact_info = []
            if contact.get('email'):
                contact_info.append(f"📧 {contact.get('email')}")
            if contact.get('phone'):
                contact_info.append(f"📞 {contact.get('phone')}")
            if contact_info:
                st.markdown(" | ".join(contact_info))
        
        # Skills section
        st.markdown("#### Skills")
        skills = parsed_data.get('skills', {})
        if skills:
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**Technical Skills**")
                tech_skills = skills.get('technical', [])
                if tech_skills:
                    for skill in tech_skills:
                        st.markdown(f"- {skill}")
                else:
                    st.markdown("*No technical skills listed*")
            
            with col2:
                st.markdown("**Soft Skills**")
                soft_skills = skills.get('soft', [])
                if soft_skills:
                    for skill in soft_skills:
                        st.markdown(f"- {skill}")
                else:
                    st.markdown("*No soft skills listed*")
        
        # Work experience
        st.markdown("#### Work Experience")
        experience = parsed_data.get('work_experience', [])
        if experience:
            for job in experience:
                if isinstance(job, dict):
                    title = job.get('title', 'Position')
                    company = job.get('company', '')
                    period = job.get('period', '')
                    description = job.get('description', '')
                    
                    job_header = f"**{title}**"
                    if company:
                        job_header += f" at {company}"
                    if period:
                        job_header += f" | {period}"
                        
                    st.markdown(job_header)
                    if description:
                        st.markdown(description)
                    st.markdown("---")
                elif isinstance(job, str):
                    st.markdown(f"- {job}")
        else:
            st.markdown("*No work experience listed*")
            
        # Education
        st.markdown("#### Education")
        education = parsed_data.get('education', [])
        if education:
            for edu in education:
                if isinstance(edu, dict):
                    degree = edu.get('degree', '')
                    institution = edu.get('institution', '')
                    year = edu.get('year', '')
                    
                    edu_text = []
                    if degree:
                        edu_text.append(str(degree))
                    if institution:
                        edu_text.append(str(institution))
                    if year:
                        edu_text.append(str(year))
                        
                    if edu_text:
                        st.markdown(f"- {' | '.join(edu_text)}")
                    else:
                        st.markdown(f"- Education entry (no details available)")
                elif isinstance(edu, str):
                    st.markdown(f"- {edu}")
                else:
                    # Handle unexpected type
                    st.markdown(f"- Education entry (format not recognized)")
        else:
            st.markdown("*No education details listed*")
            
        # Certifications
        certifications = parsed_data.get('certifications', [])
        if certifications:
            st.markdown("#### Certifications")
            for cert in certifications:
                st.markdown(f"- {cert}")
        
        st.markdown('</div>', unsafe_allow_html=True)
    elif cv_data:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown(f"### CV: {cv_data.get('cv_name', 'Unnamed CV')}")
        st.markdown(f"**Uploaded:** {cv_data.get('upload_date', 'Unknown date')}")
        
        if cv_data.get('cv_text'):
            with st.expander("View CV Text"):
                st.text(cv_data['cv_text'])
        else:
            st.markdown("*No CV text available*")
        st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.markdown("*No CV data available*")

def display_user_profile(user_data):
    """Display user profile information."""
    if not user_data:
        return
        
    st.markdown('<div class="user-profile">', unsafe_allow_html=True)
    cols = st.columns([1, 4])
    
    with cols[0]:
        # Display user avatar with initials
        initials = ""
        if user_data.get('full_name'):
            name_parts = user_data['full_name'].split()
            initials = "".join([part[0].upper() for part in name_parts if part])[:2]
        else:
            initials = user_data.get('email', '?')[0].upper()
            
        st.markdown(f'<div class="user-avatar">{initials}</div>', unsafe_allow_html=True)
        
    with cols[1]:
        # Display user info
        st.markdown(f"### {user_data.get('full_name', 'User')}")
        st.markdown(f"**Email:** {user_data.get('email', 'No email')}")
        
        # Subscription status
        if user_data.get('subscription_status') == 'active' and user_data.get('subscription_end') > datetime.now():
            days_left = (user_data['subscription_end'] - datetime.now()).days
            st.markdown(f'<span class="subscription-badge">Active Subscription • {days_left} days left</span>', unsafe_allow_html=True)
        elif user_data.get('subscription_status') == 'active':
            st.markdown(f'<span class="subscription-badge expired">Subscription Expired</span>', unsafe_allow_html=True)
        else:
            st.markdown(f'<span class="subscription-badge expired">No Active Subscription</span>', unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)

def display_pricing():
    """Display pricing information and subscription button."""
    st.markdown("## Subscription")
    
    # Pricing card
    st.markdown('<div class="pricing-card">', unsafe_allow_html=True)
    st.markdown("### CareerVertex Pro")
    st.markdown('<p class="pricing-price">£25<span class="pricing-period">/month</span></p>', unsafe_allow_html=True)
    
    # Features
    st.markdown("#### Features:")
    st.markdown('<div class="feature-item"><i>✓</i> Unlimited CV analyses</div>', unsafe_allow_html=True)
    st.markdown('<div class="feature-item"><i>✓</i> Store multiple CVs and job descriptions</div>', unsafe_allow_html=True)
    st.markdown('<div class="feature-item"><i>✓</i> Compare one CV to multiple job ads</div>', unsafe_allow_html=True)
    st.markdown('<div class="feature-item"><i>✓</i> Industry-specific insights</div>', unsafe_allow_html=True)
    st.markdown('<div class="feature-item"><i>✓</i> Custom cover letter generation</div>', unsafe_allow_html=True)
    st.markdown('<div class="feature-item"><i>✓</i> Interview preparation tips</div>', unsafe_allow_html=True)
    st.markdown('<div class="feature-item"><i>✓</i> Comprehensive reports</div>', unsafe_allow_html=True)
    
    # Subscribe button
    if 'user_id' in st.session_state and 'user_email' in st.session_state:
        if st.button("Subscribe Now", use_container_width=True):
            try:
                checkout_session = create_stripe_checkout_session(
                    st.session_state['user_id'],
                    st.session_state['user_email']
                )
                
                if checkout_session:
                    st.session_state['checkout_url'] = checkout_session.url
                    st.success("Redirecting to payment page...")
                    st.markdown(f'<meta http-equiv="refresh" content="2;URL=\'{checkout_session.url}\'">', unsafe_allow_html=True)
            except Exception as e:
                error_tracker.add_error("payment_error", "Failed to create checkout session", True, str(e))
                st.error("Failed to create checkout session. Please try again.")
    else:
        st.info("Please log in to subscribe.")
    
    st.markdown('</div>', unsafe_allow_html=True)

# === ANALYSIS FUNCTIONS ===
def parse_cv(client, cv_text, candidate_name):
    """
    Parses a CV and returns a dictionary with structured data.
    """
    if not cv_text or len(cv_text.strip()) < 50:
        error_tracker.add_error("parse_error", "Your CV contains too little text to parse effectively.", False)
        # Return fallback structure
        return {
            "name": candidate_name,
            "contact_info": {"email": None, "phone": None},
            "education": [],
            "work_experience": [{"title": "Unknown", "description": "CV text extraction failed or contained too little text."}],
            "skills": {"technical": [], "soft": []},
            "certifications": [],
            "original_filename": candidate_name,
            "parsing_error": "Text extraction failed or insufficient content"
        }

    prompt = f"""
    Please extract the following information from the CV provided below for candidate '{candidate_name}'.
    Structure the output as a single JSON object containing these keys:
    - "name": (string, if found, otherwise use '{candidate_name}')
    - "contact_info": (object with "email" and "phone" keys, strings, null if not found)
    - "education": (array of strings or objects describing education, empty array if none)
    - "work_experience": (array of strings or objects describing work experience including years/duration, empty array if none)
    - "skills": (object with "technical" and "soft" keys, each containing an array of strings, empty arrays if none)
    - "certifications": (array of strings, empty array if none)
    - "original_filename": (string, always include '{candidate_name}')

    IMPORTANT: Respond ONLY with the valid JSON object. Do not include any introductory text, explanations, or markdown formatting like ```json.

    CV for candidate {candidate_name}:
    ---
    {cv_text}
    ---
    """

    # Use enhanced API call with timeout
    success, response_text = call_anthropic_api_with_timeout(
        client=client,
        prompt=prompt,
        max_tokens=1500,
        temperature=0.0,
        system="You are an expert CV parser. Extract structured information accurately and return ONLY a valid JSON object as specified.",
        timeout=45,  # 45 second timeout
        retries=1    # 1 retry attempt
    )

    if not success:
        error_tracker.add_error("api_error", f"API call failed during CV parsing: {response_text}", True)
        # Return fallback structure on API failure
        return {
            "name": candidate_name,
            "contact_info": {"email": None, "phone": None},
            "education": [],
            "work_experience": [{"title": "Unknown", "description": "API call failed during CV parsing."}],
            "skills": {"technical": [], "soft": []},
            "certifications": [],
            "original_filename": candidate_name,
            "parsing_error": f"API Error: {response_text}"
        }

    # Prepare fallback structure for JSON parsing failures
    fallback_structure = {
        "name": candidate_name,
        "contact_info": {"email": None, "phone": None},
        "education": [],
        "work_experience": [],
        "skills": {"technical": [], "soft": []},
        "certifications": [],
        "original_filename": candidate_name,
        "parsing_error": "JSON parsing failed"
    }

    # Extract JSON with structured fallbacks
    json_string = extract_json_from_string(response_text, json.dumps(fallback_structure))
    
    try:
        parsed_data = json.loads(json_string)
        
        # Ensure it's a dictionary
        if not isinstance(parsed_data, dict):
            error_tracker.add_error("json_error", f"Parsing returned {type(parsed_data).__name__} instead of a dictionary.", True)
            return fallback_structure
            
        # Validate and ensure essential fields exist
        if 'original_filename' not in parsed_data:
            parsed_data['original_filename'] = candidate_name
        if 'name' not in parsed_data or not parsed_data['name']:
            parsed_data['name'] = candidate_name
        
        # Ensure proper structure for nested objects
        if 'contact_info' not in parsed_data or not isinstance(parsed_data['contact_info'], dict):
            parsed_data['contact_info'] = {"email": None, "phone": None}
        if 'skills' not in parsed_data or not isinstance(parsed_data['skills'], dict):
            parsed_data['skills'] = {"technical": [], "soft": []}
            
        # Ensure arrays for collections
        for field in ['education', 'work_experience', 'certifications']:
            if field not in parsed_data or not isinstance(parsed_data[field], list):
                parsed_data[field] = []
                
        return parsed_data
        
    except json.JSONDecodeError as json_e:
        error_tracker.add_error("json_error", f"Failed to decode JSON response: {json_e}", True)
        return fallback_structure

def analyze_cv_match(client, cv_data, job_description):
    """
    Analyses how well a CV matches with a job description.
    Returns a match analysis with scores and recommendations.
    """
    if not cv_data or not cv_data.get('parsed_data'):
        error_tracker.add_error("parse_error", "No CV data provided for analysis.", True)
        return None
        
    if not job_description or len(job_description.strip()) < 50:
        error_tracker.add_error("parse_error", "Job description is too short for meaningful analysis.", False)
        job_description += "\n\nThis is a professional position requiring technical skills and relevant experience."

    # Convert CV data to a JSON string for the prompt
    try:
        cv_json_string = json.dumps(cv_data['parsed_data'], indent=2)
    except Exception as e:
        error_tracker.add_error("json_error", "Error converting CV data to JSON", True, str(e))
        return None

    prompt = f"""
    You are an expert job application consultant. Based on the job description below and the provided CV data, 
    analyse how well the candidate matches the job requirements and provide constructive feedback.

    Job Description:
    ---
    {job_description}
    ---

    CV Data (JSON):
    ---
    {cv_json_string}
    ---

    Perform a thorough analysis of the match between this candidate and the job description, including:
    1. An overall "match_score" from 0 to 100, representing their fit for the position.
    2. Three to five key "strengths" that make them a good fit for this specific role.
    3. Three to five main "improvement_areas" where they could enhance their candidacy.
    4. A "skills_assessment" object with ratings (0-100) for these specific categories:
       - "Technical Skills" (relevance to the role)
       - "Experience" (years and quality related to the role)
       - "Education" (relevance and level)
       - "CV Quality" (clarity, formatting, and presentation)
    5. "recommendations" - practical, specific suggestions to improve their CV and application for this role.
    6. "keyword_analysis" - identify key terms from the job description missing from their CV.
    7. "industry_fit" - assessment of how well the candidate matches the industry requirements for this role.
    8. "potential_job_titles" - alternate job titles that this CV would be well-suited for.
    9. "experience_gap_analysis" - identify specific experience gaps between the CV and job requirements.

    Structure your response as a single, valid JSON object containing these keys.
    Be constructive, honest but encouraging, highlighting both positives and areas for improvement.
    """

    # Use enhanced API call with timeout
    success, response_text = call_anthropic_api_with_timeout(
        client=client,
        prompt=prompt,
        max_tokens=2500,
        temperature=0.1,
        system="You are a professional job application consultant providing detailed, honest but constructive feedback to help job seekers improve their applications.",
        timeout=60,  # 60 second timeout
        retries=1    # 1 retry attempt
    )

    if not success:
        error_tracker.add_error("api_error", f"API call failed during CV analysis: {response_text}", True)
        # Return a basic fallback analysis
        return {
            "match_score": 50, 
            "strengths": ["Unable to analyze due to API error"],
            "improvement_areas": ["Unable to analyze due to API error"],
            "skills_assessment": {
                "Technical Skills": 50,
                "Experience": 50,
                "Education": 50,
                "CV Quality": 50
            },
            "recommendations": ["Please try again later or contact support."],
            "keyword_analysis": ["Analysis unavailable"],
            "analysis_error": f"API Error: {response_text}"
        }

    # Prepare fallback structure
    fallback_analysis = {
        "match_score": 50, 
        "strengths": ["Data extraction failed - please try again"],
        "improvement_areas": ["Data extraction failed - please try again"],
        "skills_assessment": {
            "Technical Skills": 50,
            "Experience": 50,
            "Education": 50,
            "CV Quality": 50
        },
        "recommendations": ["Please try again or contact support."],
        "keyword_analysis": ["Analysis unavailable"],
        "industry_fit": "Unknown",
        "potential_job_titles": ["Unable to determine"],
        "experience_gap_analysis": ["Analysis unavailable"],
        "analysis_error": "JSON parsing failed"
    }
    
    # Extract JSON with structured fallbacks
    json_string = extract_json_from_string(response_text, json.dumps(fallback_analysis))
    
    try:
        analysis_data = json.loads(json_string)
        
        # Basic validation
        if not isinstance(analysis_data, dict):
            error_tracker.add_error("json_error", f"Analysis returned {type(analysis_data).__name__} instead of a dictionary.", True)
            return fallback_analysis
            
        # Ensure all required fields exist
        required_fields = [
            "match_score", "strengths", "improvement_areas", 
            "skills_assessment", "recommendations", "keyword_analysis",
            "industry_fit", "potential_job_titles", "experience_gap_analysis"
        ]
        
        for field in required_fields:
            if field not in analysis_data:
                if field in ["strengths", "improvement_areas", "recommendations", "keyword_analysis", "potential_job_titles", "experience_gap_analysis"]:
                    analysis_data[field] = ["Data missing"]
                elif field == "skills_assessment":
                    analysis_data[field] = {
                        "Technical Skills": 50,
                        "Experience": 50,
                        "Education": 50,
                        "CV Quality": 50
                    }
                elif field == "match_score":
                    analysis_data[field] = 50
                elif field == "industry_fit":
                    analysis_data[field] = "Unknown"
        
        return analysis_data
        
    except json.JSONDecodeError as json_e:
        error_tracker.add_error("json_error", f"Failed to decode analysis JSON: {json_e}", True)
        return fallback_analysis

def generate_interview_tips(client, cv_data, job_description, analysis):
    """
    Generates personalised interview tips based on CV and job description.
    """
    if not cv_data or not job_description or not analysis:
        return ["Unable to generate interview tips due to missing data."]
    
    # Extract key areas where improvement might be needed
    improvement_areas = analysis.get('improvement_areas', [])
    strengths = analysis.get('strengths', [])
    match_score = analysis.get('match_score', 50)
    
    # Convert data to JSON for the prompt
    try:
        cv_json = json.dumps(cv_data['parsed_data'], indent=2)
        analysis_json = json.dumps(analysis, indent=2)
    except Exception as e:
        error_tracker.add_error("json_error", f"Error preparing data for interview tips: {e}", False)
        return ["Error generating interview tips."]
    
    prompt = f"""
    You are an expert career coach. Based on this candidate's CV and job description analysis, 
    provide 5 strategic interview preparation tips tailored specifically to them.

    Job Description:
    ---
    {job_description}
    ---

    CV Data:
    ---
    {cv_json}
    ---
    
    CV Analysis:
    ---
    {analysis_json}
    ---

    Provide 5 specific, actionable interview tips that will help this candidate:
    1. Emphasise their relevant strengths for this position
    2. Address potential concerns about improvement areas
    3. Prepare for likely questions based on the gap between their profile and job requirements
    4. Highlight their unique value proposition for this role
    5. Showcase their enthusiasm and fit for the company/role

    Format each tip with a clear heading and explanation. Be specific, practical and constructive.
    Tailor these tips precisely to this candidate and this job - avoid generic advice.
    """

    # Use enhanced API call with timeout
    success, response_text = call_anthropic_api_with_timeout(
        client=client,
        prompt=prompt,
        max_tokens=1500,
        temperature=0.2,
        system="You are a supportive career coach providing practical, personalized interview advice.",
        timeout=30,
        retries=1
    )
    
    if not success:
        return ["Unable to generate interview tips. Please try again later."]
    
    # Just return the text directly as it's already formatted
    return response_text

def analyze_industry_fit(client, cv_data, job_description, analysis):
    """
    Analyzes how well the candidate fits within the specific industry context.
    """
    if not cv_data or not job_description or not analysis:
        return None
    
    # Convert data to JSON for the prompt
    try:
        cv_json = json.dumps(cv_data['parsed_data'], indent=2)
        analysis_json = json.dumps(analysis, indent=2)
    except Exception as e:
        error_tracker.add_error("json_error", f"Error preparing data for industry analysis: {e}", False)
        return None
    
    prompt = f"""
    You are an expert industry analyst specialising in career placement. Based on this candidate's CV, 
    the job description, and previous analysis, provide an industry-specific assessment.

    Job Description:
    ---
    {job_description}
    ---

    CV Data:
    ---
    {cv_json}
    ---
    
    CV Analysis:
    ---
    {analysis_json}
    ---

    Provide a JSON response with the following structure:
    1. "industry_identified": the specific industry this job is in
    2. "industry_fit_score": numeric score from 0-100 on industry fit
    3. "industry_trends": array of current trends in this industry relevant to the role
    4. "industry_keywords": array of industry-specific keywords that would strengthen the CV
    5. "competitors": array of top companies in this space the candidate should research
    6. "industry_challenges": array of current challenges in this industry the candidate should be aware of
    7. "salary_range": object with "min" and "max" fields showing typical salary range for this role in this industry
    
    Structure your response as a single, valid JSON object containing these keys.
    """

    # Use enhanced API call with timeout
    success, response_text = call_anthropic_api_with_timeout(
        client=client,
        prompt=prompt,
        max_tokens=1500,
        temperature=0.1,
        system="You are an expert industry analyst providing accurate industry insights for job seekers.",
        timeout=30,
        retries=1
    )
    
    if not success:
        return None
    
    # Prepare fallback structure
    fallback_industry = {
        "industry_identified": "Unknown",
        "industry_fit_score": 50,
        "industry_trends": ["Unable to analyze industry trends"],
        "industry_keywords": ["Unable to identify industry keywords"],
        "competitors": ["Unable to identify competitors"],
        "industry_challenges": ["Unable to identify industry challenges"],
        "salary_range": {"min": 0, "max": 0}
    }
    
    # Extract JSON with structured fallbacks
    json_string = extract_json_from_string(response_text, json.dumps(fallback_industry))
    
    try:
        return json.loads(json_string)
    except json.JSONDecodeError:
        error_tracker.add_error("json_error", "Failed to decode industry analysis JSON", False)
        return fallback_industry

def generate_comprehensive_report(cv_data, job_description, analysis, industry_analysis):
    """
    Generates a detailed PDF-ready report with all analyses.
    """
    # For now, we'll generate a structured markdown report that can be saved
    report_parts = []
    
    # Title and header
    report_parts.append(f"# CV Analysis Report\n")
    report_parts.append(f"**Candidate:** {cv_data['parsed_data'].get('name', 'Candidate')}\n")
    report_parts.append(f"**Date:** {datetime.now().strftime('%B %d, %Y')}\n")
    report_parts.append(f"**Match Score:** {analysis.get('match_score', 0)}%\n")
    
    # Executive summary
    report_parts.append("## Executive Summary\n")
    strengths = analysis.get('strengths', [])
    if strengths:
        report_parts.append("### Key Strengths\n")
        for strength in strengths:
            report_parts.append(f"- {strength}\n")
    
    improvement_areas = analysis.get('improvement_areas', [])
    if improvement_areas:
        report_parts.append("\n### Areas for Improvement\n")
        for area in improvement_areas:
            report_parts.append(f"- {area}\n")
    
    # Detailed Skills Assessment
    report_parts.append("\n## Skills Assessment\n")
    skills = analysis.get('skills_assessment', {})
    for skill, rating in skills.items():
        report_parts.append(f"- **{skill}:** {rating}/100\n")
    
    # Industry Analysis
    if industry_analysis:
        report_parts.append("\n## Industry Analysis\n")
        report_parts.append(f"- **Industry:** {industry_analysis.get('industry_identified', 'Unknown')}\n")
        report_parts.append(f"- **Industry Fit:** {industry_analysis.get('industry_fit_score', 0)}/100\n")
        
        industry_trends = industry_analysis.get('industry_trends', [])
        if industry_trends:
            report_parts.append("\n### Industry Trends\n")
            for trend in industry_trends:
                report_parts.append(f"- {trend}\n")
                
        industry_keywords = industry_analysis.get('industry_keywords', [])
        if industry_keywords:
            report_parts.append("\n### Key Industry Terms\n")
            for keyword in industry_keywords:
                report_parts.append(f"- {keyword}\n")
                
        industry_challenges = industry_analysis.get('industry_challenges', [])
        if industry_challenges:
            report_parts.append("\n### Industry Challenges\n")
            for challenge in industry_challenges:
                report_parts.append(f"- {challenge}\n")
                
        competitors = industry_analysis.get('competitors', [])
        if competitors:
            report_parts.append("\n### Key Competitors\n")
            for competitor in competitors:
                report_parts.append(f"- {competitor}\n")
                
        salary_range = industry_analysis.get('salary_range', {})
        if salary_range and salary_range.get('min', 0) > 0:
            report_parts.append(f"\n**Typical Salary Range:** £{salary_range.get('min', 0):,} - £{salary_range.get('max', 0):,}\n")
    
    # Keyword Analysis
    keywords = analysis.get('keyword_analysis', [])
    if keywords:
        report_parts.append("\n## Keyword Analysis\n")
        report_parts.append("Keywords that appear in the job description but are missing or underemphasised in your CV:\n")
        for keyword in keywords:
            report_parts.append(f"- {keyword}\n")
    
    # Experience Gap Analysis
    experience_gaps = analysis.get('experience_gap_analysis', [])
    if experience_gaps:
        report_parts.append("\n## Experience Gap Analysis\n")
        for gap in experience_gaps:
            report_parts.append(f"- {gap}\n")
    
    # Recommendations
    recommendations = analysis.get('recommendations', [])
    if recommendations:
        report_parts.append("\n## Recommendations\n")
        for i, rec in enumerate(recommendations):
            report_parts.append(f"{i+1}. {rec}\n")
    
    # Final Notes
    report_parts.append("\n## Next Steps\n")
    report_parts.append("1. Update your CV based on the recommendations above\n")
    report_parts.append("2. Prepare for interviews using the interview tips provided separately\n")
    report_parts.append("3. Research the industry trends and competitors identified\n")
    report_parts.append("4. Consider applying for the alternate job titles suggested if appropriate\n")
    
    # Join all parts
    return "".join(report_parts)

def generate_cover_letter(client, cv_data, job_description, analysis):
    """
    Generates a customised cover letter based on CV, job description, and match analysis.
    """
    if not cv_data or not job_description or not analysis:
        return "Unable to generate cover letter due to missing data."
    
    # Extract key information to personalise the cover letter
    candidate_name = cv_data['parsed_data'].get('name', 'Candidate')
    strengths = analysis.get('strengths', [])
    keywords = analysis.get('keyword_analysis', [])
    skills_assessment = analysis.get('skills_assessment', {})
    
    # Convert data to JSON for the prompt
    try:
        cv_json = json.dumps(cv_data['parsed_data'], indent=2)
        analysis_json = json.dumps(analysis, indent=2)
    except Exception as e:
        error_tracker.add_error("json_error", "Error preparing data for cover letter", False, str(e))
        return "Error generating cover letter."
    
    prompt = f"""
    You are an expert career consultant. Based on this candidate's CV and the job description analysis, 
    create a professional cover letter that highlights their relevant qualifications and fit for the role.

    Job Description:
    ---
    {job_description}
    ---

    CV Data:
    ---
    {cv_json}
    ---
    
    CV Analysis:
    ---
    {analysis_json}
    ---

    Write a complete, professional cover letter that:
    1. Includes a proper salutation (use "Dear Hiring Manager" if no specific recipient is known)
    2. Has an engaging introduction that mentions the specific role they're applying for
    3. Highlights 2-3 of the candidate's key strengths and qualifications that match the job requirements
    4. Uses specific examples from their experience to demonstrate these qualifications
    5. Addresses any potential gaps or concerns tactfully (if relevant)
    6. Incorporates relevant keywords from the job description naturally
    7. Expresses enthusiasm for the role and organisation
    8. Includes a strong closing paragraph with a call to action
    9. Uses a professional sign-off

    The cover letter should be 3-4 paragraphs, professional in tone but conversational, and tailored specifically to this candidate and position.
    Use British English spelling and grammar conventions.
    """

    # Use enhanced API call with timeout
    success, response_text = call_anthropic_api_with_timeout(
        client=client,
        prompt=prompt,
        max_tokens=2000,
        temperature=0.3,
        system="You are a professional career consultant specialising in cover letter writing. Create a tailored, effective cover letter using the candidate's strengths and the job requirements.",
        timeout=45,
        retries=1
    )
    
    if not success:
        return "Unable to generate cover letter. Please try again later."
    
    # Return the cover letter text directly
    return response_text

def generate_trend_charts(analyses):
    """
    Generates charts showing trends across analyses.
    """
    if not analyses or len(analyses) < 2:
        return None
        
    # Create dataframe for analysis
    df = pd.DataFrame(
        [{
            'timestamp': analysis['created_at'],
            'job_title': analysis['job_title'],
            'company': analysis['company'],
            'match_score': analysis['analysis_data']['match_score'],
            'skills_assessment': analysis['analysis_data']['skills_assessment'],
            'analysis_id': analysis['analysis_id']
        } for analysis in analyses if 'analysis_data' in analysis and 'match_score' in analysis['analysis_data']]
    )
    
    if df.empty or len(df) < 2:
        return None
    
    # Extract skill assessment data for easier charting
    # This flattens the nested dictionary into columns
    skill_columns = []
    for idx, analysis in df.iterrows():
        skills = analysis.get('skills_assessment', {})
        for skill, value in skills.items():
            col_name = f"skill_{skill.replace(' ', '_').lower()}"
            if col_name not in df.columns:
                df[col_name] = None
            df.at[idx, col_name] = value
            if col_name not in skill_columns:
                skill_columns.append(col_name)
    
    # Ensure timestamps are datetime objects
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    # Sort by timestamp
    df = df.sort_values('timestamp')
    
    # Create charts
    charts = {}
    
    # 1. Match score over time
    match_score_chart = alt.Chart(df).mark_line(point=True).encode(
        x=alt.X('timestamp:T', title='Date'),
        y=alt.Y('match_score:Q', scale=alt.Scale(domain=[0, 100]), title='Match Score'),
        tooltip=['job_title', 'match_score', 'timestamp']
    ).properties(
        title='Match Score Trend'
    )
    charts['match_score'] = match_score_chart
    
    # 2. Skills radar chart (not directly supported in Altair, so we'll fake it with multiple lines)
    if skill_columns:
        # Reshape for the skills chart
        skills_df = df.melt(
            id_vars=['timestamp', 'job_title', 'analysis_id'],
            value_vars=skill_columns,
            var_name='skill',
            value_name='rating'
        )
        
        # Clean up skill names
        skills_df['skill'] = skills_df['skill'].str.replace('skill_', '').str.replace('_', ' ').str.title()
        
        # Create a comparative skills chart
        skills_chart = alt.Chart(skills_df).mark_line().encode(
            x=alt.X('skill:N', title='Skill Category'),
            y=alt.Y('rating:Q', scale=alt.Scale(domain=[0, 100]), title='Rating'),
            color=alt.Color('job_title:N', title='Job'),
            tooltip=['job_title', 'skill', 'rating']
        ).properties(
            title='Skills Comparison Across Job Applications'
        )
        charts['skills'] = skills_chart
    
    return charts

# === PAGES ===
def show_login_page():
    """Display login and registration form."""
    st.title("Welcome to CareerVertex")
    st.markdown("*AI-Powered CV and Job Description Analysis*")
    
    # Split into two columns
    login_col, register_col = st.columns(2)
    
    with login_col:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.subheader("Login")
        with st.form("login_form"):
            email = st.text_input("Email")
            password = st.text_input("Password", type="password")
            submit_login = st.form_submit_button("Login")
            
            if submit_login:
                if not email or not password:
                    st.error("Please enter both email and password.")
                else:
                    success, result = auth_manager.login_user(email, password)
                    if success:
                        # Store user data in session state
                        st.session_state['user_id'] = result['user_id']
                        st.session_state['user_email'] = result['email']
                        st.session_state['user_name'] = result['full_name'] if result['full_name'] else email
                        st.session_state['user_data'] = result
                        st.success("Login successful!")
                        st.rerun()
                    else:
                        st.error(result)
        st.markdown('</div>', unsafe_allow_html=True)
    
    with register_col:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.subheader("Register")
        with st.form("register_form"):
            new_email = st.text_input("Email Address")
            new_password = st.text_input("Create Password", type="password")
            confirm_password = st.text_input("Confirm Password", type="password")
            full_name = st.text_input("Full Name")
            submit_register = st.form_submit_button("Create Account")
            
            if submit_register:
                if not new_email or not new_password or not confirm_password:
                    st.error("Please fill out all required fields.")
                elif new_password != confirm_password:
                    st.error("Passwords do not match.")
                else:
                    success, result = auth_manager.register_user(new_email, new_password, full_name)
                    if success:
                        st.success("Registration successful! Please log in.")
                    else:
                        st.error(result)
        st.markdown('</div>', unsafe_allow_html=True)
    
    # App description
    st.markdown("---")
    st.markdown("## AI-Powered CV Analysis")
    st.markdown("""
    CareerVertex uses advanced AI to match your CV with job descriptions, helping you:
    
    - Understand how well your CV matches specific job requirements
    - Identify key strengths and areas for improvement
    - Get tailored recommendations to enhance your application
    - Generate customised cover letters
    - Prepare for interviews with personalised tips
    
    Subscribe today for only **£25 per month** to unlock all features!
    """)
    
    # Pricing and features
    st.markdown("---")
    pricing_col1, pricing_col2, pricing_col3 = st.columns([1, 2, 1])
    
    with pricing_col2:
        display_pricing()

def show_admin_page():
    """Display admin dashboard."""
    st.title("Admin Dashboard")
    
    admin_tabs = st.tabs(["User Management", "Usage Statistics", "Billing", "System Status"])
    
    with admin_tabs[0]:
        st.subheader("User Management")
        
        # Get all users from database
        users = db_manager.execute_query("SELECT * FROM users ORDER BY created_at DESC")
        
        if users:
            # Convert to DataFrame for easier display
            users_df = pd.DataFrame([dict(user) for user in users])
            
            # Add user status column
            users_df['status'] = users_df.apply(
                lambda x: 'Active' if x['subscription_status'] == 'active' and x['subscription_end'] > datetime.now() 
                else 'Expired' if x['subscription_status'] == 'active' 
                else 'Inactive',
                axis=1
            )
            
            # Format dates
            for date_col in ['created_at', 'last_login', 'subscription_start', 'subscription_end']:
                if date_col in users_df.columns:
                    users_df[date_col] = users_df[date_col].dt.strftime('%Y-%m-%d %H:%M')
            
            # Display user table
            st.dataframe(
                users_df[[
                    'user_id', 'email', 'full_name', 'status', 
                    'subscription_start', 'subscription_end', 'created_at', 'last_login'
                ]]
            )
            
            # User details
            selected_user = st.selectbox(
                "Select User for Details",
                options=users_df['email'].tolist(),
                format_func=lambda x: x
            )
            
            if selected_user:
                user = users_df[users_df['email'] == selected_user].iloc[0]
                
                st.markdown(f"### User: {user['full_name'] or user['email']}")
                
                # User actions
                actions_col1, actions_col2, actions_col3 = st.columns(3)
                
                with actions_col1:
                    if st.button("Reset Password"):
                        # Generate a temporary password
                        temp_password = str(uuid.uuid4())[:8]
                        
                        # Hash the password
                        password_hash = bcrypt.hashpw(temp_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                        
                        # Update in database
                        db_manager.execute_query(
                            "UPDATE users SET password_hash = %s WHERE user_id = %s",
                            (password_hash, user['user_id']),
                            fetch=False
                        )
                        
                        st.success(f"Password reset. Temporary password: {temp_password}")
                
                with actions_col2:
                    if user['status'] != 'Active':
                        if st.button("Extend Subscription (30 days)"):
                            # Set subscription dates
                            start_date = datetime.now()
                            end_date = start_date + timedelta(days=30)
                            
                            # Update in database
                            db_manager.execute_query(
                                """
                                UPDATE users 
                                SET subscription_status = 'active',
                                    subscription_start = %s,
                                    subscription_end = %s
                                WHERE user_id = %s
                                """,
                                (start_date, end_date, user['user_id']),
                                fetch=False
                            )
                            
                            st.success(f"Subscription extended by 30 days.")
                            st.rerun()
                    else:
                        if st.button("Cancel Subscription"):
                            # Update in database
                            db_manager.execute_query(
                                "UPDATE users SET subscription_status = 'inactive' WHERE user_id = %s",
                                (user['user_id'],),
                                fetch=False
                            )
                            
                            st.success(f"Subscription canceled.")
                            st.rerun()
                
                with actions_col3:
                    if st.button("Delete User", type="primary"):
                        # Confirm deletion
                        confirm = st.checkbox("I understand this will permanently delete the user and all their data")
                        
                        if confirm:
                            # Delete related records first
                            db_manager.execute_query(
                                "DELETE FROM token_usage WHERE user_id = %s",
                                (user['user_id'],),
                                fetch=False
                            )
                            
                            db_manager.execute_query(
                                "DELETE FROM analyses WHERE user_id = %s",
                                (user['user_id'],),
                                fetch=False
                            )
                            
                            db_manager.execute_query(
                                "DELETE FROM job_descriptions WHERE user_id = %s",
                                (user['user_id'],),
                                fetch=False
                            )
                            
                            db_manager.execute_query(
                                "DELETE FROM cvs WHERE user_id = %s",
                                (user['user_id'],),
                                fetch=False
                            )
                            
                            db_manager.execute_query(
                                "DELETE FROM payments WHERE user_id = %s",
                                (user['user_id'],),
                                fetch=False
                            )
                            
                            # Finally delete the user
                            db_manager.execute_query(
                                "DELETE FROM users WHERE user_id = %s",
                                (user['user_id'],),
                                fetch=False
                            )
                            
                            st.success(f"User deleted successfully.")
                            st.rerun()
                
                # User statistics
                st.subheader("User Statistics")
                
                # Get token usage
                token_usage = db_manager.execute_query(
                    """
                    SELECT SUM(tokens_used) as total_tokens, COUNT(*) as request_count
                    FROM token_usage
                    WHERE user_id = %s
                    """,
                    (user['user_id'],)
                )
                
                # Get analysis count
                analysis_count = db_manager.execute_query(
                    """
                    SELECT COUNT(*) as count
                    FROM analyses
                    WHERE user_id = %s
                    """,
                    (user['user_id'],)
                )
                
                # Get CV count
                cv_count = db_manager.execute_query(
                    """
                    SELECT COUNT(*) as count
                    FROM cvs
                    WHERE user_id = %s
                    """,
                    (user['user_id'],)
                )
                
                # Display stats
                stats_col1, stats_col2, stats_col3 = st.columns(3)
                
                with stats_col1:
                    st.metric("Total API Requests", token_usage[0]['request_count'] if token_usage else 0)
                
                with stats_col2:
                    st.metric("Total Tokens Used", f"{token_usage[0]['total_tokens']:,}" if token_usage and token_usage[0]['total_tokens'] else 0)
                
                with stats_col3:
                    st.metric("Analyses Performed", analysis_count[0]['count'] if analysis_count else 0)
        else:
            st.info("No users found in the database.")
    
    with admin_tabs[1]:
        st.subheader("Usage Statistics")
        
        # Get token usage by day
        token_usage_by_day = db_manager.execute_query(
            """
            SELECT DATE(request_date) as date, SUM(tokens_used) as tokens, COUNT(*) as requests
            FROM token_usage
            GROUP BY DATE(request_date)
            ORDER BY date DESC
            LIMIT 30
            """
        )
        
        if token_usage_by_day:
            # Convert to DataFrame
            usage_df = pd.DataFrame([dict(row) for row in token_usage_by_day])
            
            # Create chart
            usage_chart = alt.Chart(usage_df).mark_bar().encode(
                x=alt.X('date:T', title='Date'),
                y=alt.Y('tokens:Q', title='Tokens Used'),
                tooltip=['date', 'tokens', 'requests']
            ).properties(
                title='Token Usage by Day',
                height=300
            )
            
            st.altair_chart(usage_chart, use_container_width=True)
            
            # Display table
            st.dataframe(usage_df)
            
            # Total usage
            total_tokens = db_manager.execute_query(
                """
                SELECT SUM(tokens_used) as total_tokens, COUNT(*) as request_count
                FROM token_usage
                """
            )
            
            if total_tokens:
                st.info(f"Total tokens used: {total_tokens[0]['total_tokens']:,} across {total_tokens[0]['request_count']} requests")
        else:
            st.info("No usage data available yet.")
    
    with admin_tabs[2]:
        st.subheader("Billing Information")
        
        # Get payment information
        payments = db_manager.execute_query(
            """
            SELECT p.*, u.email, u.full_name
            FROM payments p
            JOIN users u ON p.user_id = u.user_id
            ORDER BY p.payment_date DESC
            LIMIT 100
            """
        )
        
        if payments:
            # Convert to DataFrame
            payments_df = pd.DataFrame([dict(payment) for payment in payments])
            
            # Format dates
            payments_df['payment_date'] = pd.to_datetime(payments_df['payment_date']).dt.strftime('%Y-%m-%d %H:%M')
            
            # Display table
            st.dataframe(
                payments_df[[
                    'payment_id', 'email', 'full_name', 'amount', 
                    'currency', 'payment_date', 'payment_method', 'status'
                ]]
            )
            
            # Summary stats
            total_revenue = payments_df['amount'].sum()
            st.success(f"Total revenue: £{total_revenue:,.2f} from {len(payments_df)} payments")
        else:
            st.info("No payment data available yet.")
        
        # Subscription status summary
        subscription_status = db_manager.execute_query(
            """
            SELECT 
                COUNT(*) as total_users,
                SUM(CASE WHEN subscription_status = 'active' AND subscription_end > NOW() THEN 1 ELSE 0 END) as active_users,
                SUM(CASE WHEN subscription_status = 'active' AND subscription_end <= NOW() THEN 1 ELSE 0 END) as expired_users,
                SUM(CASE WHEN subscription_status != 'active' THEN 1 ELSE 0 END) as inactive_users
            FROM users
            """
        )
        
        if subscription_status:
            status = subscription_status[0]
            
            # Display summary
            stats_col1, stats_col2, stats_col3, stats_col4 = st.columns(4)
            
            with stats_col1:
                st.metric("Total Users", status['total_users'])
            
            with stats_col2:
                st.metric("Active Subscriptions", status['active_users'])
            
            with stats_col3:
                st.metric("Expired Subscriptions", status['expired_users'])
            
            with stats_col4:
                st.metric("Never Subscribed", status['inactive_users'])
        
    with admin_tabs[3]:
        st.subheader("System Status")
        
        # Display database connection status
        db_status = "Connected" if db_manager.conn_pool else "Disconnected"
        
        # Display API key status
        api_key_status = "Configured" if "ANTHROPIC_API_KEY" in st.secrets else "Missing"
        
        # Display Stripe configuration status
        stripe_status = "Configured" if "STRIPE_SECRET_KEY" in st.secrets else "Missing"
        
        # Display table sizes
        table_sizes = db_manager.execute_query(
            """
            SELECT 
                (SELECT COUNT(*) FROM users) as users_count,
                (SELECT COUNT(*) FROM cvs) as cvs_count,
                (SELECT COUNT(*) FROM job_descriptions) as job_descriptions_count,
                (SELECT COUNT(*) FROM analyses) as analyses_count,
                (SELECT COUNT(*) FROM token_usage) as token_usage_count,
                (SELECT COUNT(*) FROM payments) as payments_count
            """
        )
        
        # Display status information
        status_col1, status_col2 = st.columns(2)
        
        with status_col1:
            st.markdown("### Connection Status")
            st.markdown(f"**Database:** {db_status}")
            st.markdown(f"**Anthropic API:** {api_key_status}")
            st.markdown(f"**Stripe Integration:** {stripe_status}")
        
        with status_col2:
            if table_sizes:
                st.markdown("### Database Statistics")
                st.markdown(f"**Users:** {table_sizes[0]['users_count']}")
                st.markdown(f"**CVs:** {table_sizes[0]['cvs_count']}")
                st.markdown(f"**Job Descriptions:** {table_sizes[0]['job_descriptions_count']}")
                st.markdown(f"**Analyses:** {table_sizes[0]['analyses_count']}")
                st.markdown(f"**Token Usage Records:** {table_sizes[0]['token_usage_count']}")
                st.markdown(f"**Payment Records:** {table_sizes[0]['payments_count']}")
        
        # Server information
        st.markdown("### Server Information")
        st.code(f"""
        Streamlit version: {st.__version__}
        Anthropic client version: {anthropic.__version__}
        Python version: {os.sys.version}
        """)

def show_dashboard():
    """Display user dashboard."""
    # Get updated user data
    user_data = None
    if 'user_id' in st.session_state:
        user_data = auth_manager.get_user_data(st.session_state['user_id'])
        if user_data:
            st.session_state['user_data'] = user_data
    
    # Check if user has active subscription
    has_subscription = False
    if user_data:
        has_subscription = auth_manager.check_subscription(user_data['user_id'])
    
    # User profile in sidebar
    with st.sidebar:
        st.title("User Profile")
        
        # User profile
        if user_data:
            display_user_profile(user_data)
            
            # Logout button
            if st.button("Logout"):
                auth_manager.logout_user()
                st.rerun()
        
        # Manage subscription
        st.markdown("---")
        if user_data and not has_subscription:
            st.warning("Your subscription is not active.")
            if st.button("Subscribe Now"):
                try:
                    checkout_session = create_stripe_checkout_session(
                        user_data['user_id'],
                        user_data['email']
                    )
                    
                    if checkout_session:
                        st.session_state['checkout_url'] = checkout_session.url
                        st.success("Redirecting to payment page...")
                        st.markdown(f'<meta http-equiv="refresh" content="2;URL=\'{checkout_session.url}\'">', unsafe_allow_html=True)
                except Exception as e:
                    error_tracker.add_error("payment_error", "Failed to create checkout session", True, str(e))
                    st.error("Failed to create checkout session. Please try again.")
        
        # Information about the app
        st.markdown("---")
        st.markdown("### About CareerVertex")
        st.markdown("""
        CareerVertex analyses your CV against job descriptions to:
        
        - Score your match with the position
        - Identify strengths and improvement areas
        - Suggest industry-specific keywords
        - Generate custom cover letters
        - Provide interview preparation tips
        
        Your CV is stored securely in our database for easy comparison with multiple job descriptions.
        """)
    
    # Main content
    st.title("CareerVertex - CV Job Match Analyser")
    st.markdown("*Analyse how well your CV matches specific job descriptions*")
    
    # Check if user has subscription - if not, show pricing and subscription page
    if not has_subscription:
        st.warning("You need an active subscription to use CareerVertex features.")
        display_pricing()
        return
    
    # Initialize Anthropic client
    client = initialize_anthropic_client()
    if not client:
        st.error("Unable to initialize AI client. Please try again later.")
        return
    
    # Main dashboard tabs
    dashboard_tabs = st.tabs(["Analyse New Job", "My CVs", "My Analyses", "My Account"])
    
    # ANALYSE NEW JOB TAB
    with dashboard_tabs[0]:
        st.header("Analyse CV Against Job Description")
        
        # Get user's CVs
        user_cvs = get_user_cvs(st.session_state['user_id'])
        
        # Split into two columns
        col1, col2 = st.columns(2, gap="medium")
        
        with col1:
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.subheader("Job Description")
            # Text area for job description
            job_description = st.text_area(
                "Paste the job description here",
                height=300,
                placeholder="Copy and paste the job description you're applying for..."
            )
            
            # Job details
            job_title = st.text_input("Job Title", placeholder="Enter the position title")
            company = st.text_input("Company", placeholder="Enter the company name (optional)")
            
            # File uploader for job description
            jd_file = st.file_uploader(
                "Or upload a job description file", 
                type=["pdf", "docx", "txt"], 
                key="jd_uploader"
            )
            
            if jd_file:
                with st.spinner("Extracting job description text..."):
                    jd_text = extract_text_from_file(jd_file)
                    if jd_text:
                        job_description = jd_text
                        st.success(f"Extracted text from {jd_file.name}")
            st.markdown('</div>', unsafe_allow_html=True)
        
        with col2:
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.subheader("Your CV")
            
            # Check if user has any CVs
            if user_cvs:
                # Let user select from existing CVs or upload a new one
                cv_option = st.radio(
                    "Select CV source:",
                    ["Use existing CV", "Upload new CV"]
                )
                
                if cv_option == "Use existing CV":
                    # Display dropdown of existing CVs
                    selected_cv = st.selectbox(
                        "Select your CV",
                        options=[cv['cv_id'] for cv in user_cvs],
                        format_func=lambda x: next((cv['cv_name'] for cv in user_cvs if cv['cv_id'] == x), "Unknown CV")
                    )
                    
                    # Show CV details
                    if selected_cv:
                        cv_data = next((cv for cv in user_cvs if cv['cv_id'] == selected_cv), None)
                        if cv_data:
                            st.info(f"Selected CV: {cv_data['cv_name']} (uploaded {cv_data['upload_date'].strftime('%d %b %Y')})")
                            
                            # Check if CV has been parsed
                            if not cv_data.get('parsed_data'):
                                with st.spinner("Parsing CV..."):
                                    # Parse CV if not already parsed
                                    parsed_data = parse_cv(client, cv_data['cv_text'], cv_data['cv_name'])
                                    
                                    if parsed_data:
                                        # Update CV with parsed data
                                        update_cv_parsed_data(cv_data['cv_id'], parsed_data)
                                        cv_data['parsed_data'] = parsed_data
                else:
                    # Upload new CV
                    cv_file = st.file_uploader(
                        "Upload your CV (PDF, DOCX, or TXT)",
                        type=["pdf", "docx", "txt"],
                        key="cv_uploader"
                    )
                    
                    cv_name = st.text_input("CV Name", placeholder="Give your CV a name")
                    
                    if cv_file and cv_name:
                        with st.spinner("Extracting text from CV..."):
                            cv_text = extract_text_from_file(cv_file)
                            
                            if cv_text:
                                # Save CV to database
                                success, cv_id = save_cv(st.session_state['user_id'], cv_name, cv_text)
                                
                                if success:
                                    # Parse CV
                                    with st.spinner("Parsing CV..."):
                                        parsed_data = parse_cv(client, cv_text, cv_name)
                                        
                                        if parsed_data:
                                            # Update CV with parsed data
                                            update_cv_parsed_data(cv_id, parsed_data)
                                            
                                            # Get the full CV data
                                            cv_data = get_cv_by_id(cv_id)
                                            
                                            # Set as selected CV
                                            selected_cv = cv_id
                                            
                                            st.success(f"CV '{cv_name}' uploaded and parsed successfully!")
            else:
                # No existing CVs, must upload new one
                st.info("You don't have any CVs uploaded yet. Please upload one to continue.")
                
                cv_file = st.file_uploader(
                    "Upload your CV (PDF, DOCX, or TXT)",
                    type=["pdf", "docx", "txt"],
                    key="cv_uploader"
                )
                
                cv_name = st.text_input("CV Name", placeholder="Give your CV a name")
                
                if cv_file and cv_name:
                    with st.spinner("Extracting text from CV..."):
                        cv_text = extract_text_from_file(cv_file)
                        
                        if cv_text:
                            # Save CV to database
                            success, cv_id = save_cv(st.session_state['user_id'], cv_name, cv_text)
                            
                            if success:
                                # Parse CV
                                with st.spinner("Parsing CV..."):
                                    parsed_data = parse_cv(client, cv_text, cv_name)
                                    
                                    if parsed_data:
                                        # Update CV with parsed data
                                        update_cv_parsed_data(cv_id, parsed_data)
                                        
                                        # Get the full CV data
                                        cv_data = get_cv_by_id(cv_id)
                                        
                                        # Set as selected CV
                                        selected_cv = cv_id
                                        
                                        st.success(f"CV '{cv_name}' uploaded and parsed successfully!")
            st.markdown('</div>', unsafe_allow_html=True)
        
        # Analysis button
        analyze_col1, analyze_col2, analyze_col3 = st.columns([1, 2, 1])
        with analyze_col2:
            # Check if we have all required data
            can_analyse = (
                'selected_cv' in locals() and 
                selected_cv and 
                job_description and
                len(job_description.strip()) > 50
            )
            
            if st.button(
                "Analyse CV Match", 
                type="primary",
                disabled=not can_analyse,
                use_container_width=True
            ):
                if can_analyse:
                    # Get the CV data
                    cv_data = get_cv_by_id(selected_cv)
                    
                    if cv_data:
                        # Create progress container
                        progress_container = st.container()
                        
                        with progress_container:
                            progress_bar = st.progress(0.0)
                            status_text = st.empty()
                            
                            # Save job description
                            status_text.text("Saving job description...")
                            success, job_description_id = save_job_description(
                                st.session_state['user_id'],
                                job_title or "Untitled Position",
                                company or "",
                                job_description
                            )
                            progress_bar.progress(0.15)
                            
                            if success:
                                # Analyse match
                                status_text.text("Analysing CV match with job description...")
                                analysis_results = analyze_cv_match(client, cv_data, job_description)
                                progress_bar.progress(0.50)
                                
                                if analysis_results:
                                    # Save analysis results
                                    status_text.text("Saving analysis results...")
                                    match_score = analysis_results.get('match_score', 0)
                                    save_success, analysis_id = save_analysis_result(
                                        st.session_state['user_id'],
                                        selected_cv,
                                        job_description_id,
                                        match_score,
                                        analysis_results
                                    )
                                    progress_bar.progress(0.85)
                                    
                                    if save_success:
                                        # Industry analysis - new feature
                                        status_text.text("Conducting industry-specific analysis...")
                                        industry_analysis = analyze_industry_fit(client, cv_data, job_description, analysis_results)
                                        progress_bar.progress(1.0)
                                        
                                        # Store in session state
                                        st.session_state['current_analysis_id'] = analysis_id
                                        
                                        # Redirect to analysis results
                                        status_text.success("Analysis complete! View your results in the 'My Analyses' tab.")
                                        st.session_state['show_analysis_tab'] = True
                                        st.rerun()
                                    else:
                                        status_text.error("Failed to save analysis results. Please try again.")
                                else:
                                    status_text.error("Failed to analyse CV match. Please try again.")
                            else:
                                status_text.error("Failed to save job description. Please try again.")
        
        # Display any errors that were tracked
        error_tracker.display_errors()
    
    # MY CVS TAB
    with dashboard_tabs[1]:
        st.header("My CVs")
        
        # Get user's CVs
        user_cvs = get_user_cvs(st.session_state['user_id'])
        
        # Upload new CV button
        with st.expander("Upload New CV", expanded=not user_cvs):
            col1, col2 = st.columns(2)
            
            with col1:
                cv_file = st.file_uploader(
                    "Upload your CV (PDF, DOCX, or TXT)",
                    type=["pdf", "docx", "txt"],
                    key="cv_uploader_tab"
                )
            
            with col2:
                cv_name = st.text_input("CV Name", placeholder="Give your CV a name", key="cv_name_tab")
                
                if st.button("Upload CV", disabled=not (cv_file and cv_name)):
                    with st.spinner("Extracting text from CV..."):
                        cv_text = extract_text_from_file(cv_file)
                        
                        if cv_text:
                            # Save CV to database
                            success, cv_id = save_cv(st.session_state['user_id'], cv_name, cv_text)
                            
                            if success:
                                # Parse CV
                                with st.spinner("Parsing CV..."):
                                    parsed_data = parse_cv(client, cv_text, cv_name)
                                    
                                    if parsed_data:
                                        # Update CV with parsed data
                                        update_cv_parsed_data(cv_id, parsed_data)
                                        st.success(f"CV '{cv_name}' uploaded and parsed successfully!")
                                        st.rerun()
        
        # Display existing CVs
        if user_cvs:
            st.subheader(f"Your CVs ({len(user_cvs)})")
            
            # Create a grid of cards for CVs
            for i in range(0, len(user_cvs), 2):
                cols = st.columns(2)
                
                for j in range(2):
                    if i + j < len(user_cvs):
                        cv = user_cvs[i + j]
                        
                        with cols[j]:
                            st.markdown('<div class="card">', unsafe_allow_html=True)
                            st.markdown(f"### {cv['cv_name']}")
                            st.markdown(f"Uploaded: {cv['upload_date'].strftime('%d %b %Y')}")
                            
                            # Check if CV has been parsed
                            if cv.get('parsed_data'):
                                with st.expander("View CV Summary"):
                                    display_cv_summary(cv)
                            else:
                                with st.spinner("Parsing CV..."):
                                    # Parse CV if not already parsed
                                    parsed_data = parse_cv(client, cv['cv_text'], cv['cv_name'])
                                    
                                    if parsed_data:
                                        # Update CV with parsed data
                                        update_cv_parsed_data(cv['cv_id'], parsed_data)
                                        cv['parsed_data'] = parsed_data
                                        
                                        with st.expander("View CV Summary"):
                                            display_cv_summary(cv)
                            
                            # Action buttons
                            col1, col2 = st.columns(2)
                            
                            with col1:
                                if st.button("Use for Analysis", key=f"use_{cv['cv_id']}"):
                                    # Switch to analysis tab with this CV selected
                                    st.session_state['selected_cv_id'] = cv['cv_id']
                                    st.session_state['show_analysis_tab'] = True
                                    st.rerun()
                            
                            with col2:
                                if st.button("Delete CV", key=f"delete_{cv['cv_id']}"):
                                    # Delete confirmation
                                    if st.checkbox(f"Confirm deletion of '{cv['cv_name']}'", key=f"confirm_{cv['cv_id']}"):
                                        # First check if CV is used in any analyses
                                        analyses = db_manager.execute_query(
                                            "SELECT * FROM analyses WHERE cv_id = %s",
                                            (cv['cv_id'],)
                                        )
                                        
                                        if analyses:
                                            # Delete related analyses first
                                            db_manager.execute_query(
                                                "DELETE FROM analyses WHERE cv_id = %s",
                                                (cv['cv_id'],),
                                                fetch=False
                                            )
                                        
                                        # Delete CV
                                        db_manager.execute_query(
                                            "DELETE FROM cvs WHERE cv_id = %s",
                                            (cv['cv_id'],),
                                            fetch=False
                                        )
                                        
                                        st.success(f"CV '{cv['cv_name']}' deleted successfully!")
                                        st.rerun()
                            st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.info("You don't have any CVs uploaded yet. Please upload one using the form above.")
    
    # MY ANALYSES TAB
    with dashboard_tabs[2]:
        st.header("My Analyses")
        
        # Show analysis tab if coming from analyse button
        if st.session_state.get('show_analysis_tab', False):
            st.session_state['show_analysis_tab'] = False
            
            if 'current_analysis_id' in st.session_state:
                # Get the analysis
                analysis_data = get_analysis_by_id(st.session_state['current_analysis_id'])
                
                if analysis_data:
                    # Display analysis results
                    st.subheader(f"Analysis Results: {analysis_data['job_title']}")
                    
                    # Convert JSON data
                    analysis = analysis_data['analysis_data']
                    
                    # Main score section
                    st.markdown('<div class="card">', unsafe_allow_html=True)
                    score_col1, score_col2 = st.columns([1, 3])
                    
                    with score_col1:
                        match_score = analysis.get('match_score', 0)
                        display_match_score(match_score)
                    
                    with score_col2:
                        # Skill assessment visualization
                        st.subheader("Skills Assessment")
                        skills_assessment = analysis.get('skills_assessment', {})
                        
                        skills_chart = create_skills_chart(skills_assessment)
                        if skills_chart:
                            st.altair_chart(skills_chart, use_container_width=True)
                    st.markdown('</div>', unsafe_allow_html=True)
                    
                    # Strengths and improvement areas
                    display_strengths_and_improvements(
                        strengths=analysis.get('strengths', []), 
                        improvements=analysis.get('improvement_areas', [])
                    )
                    
                    # Detailed analysis tabs
                    analysis_detail_tabs = st.tabs([
                        "Recommendations", "Keywords", "Industry Insights", "Interview Tips", "Full Report"
                    ])
                    
                    with analysis_detail_tabs[0]:
                        # Recommendations
                        display_recommendations(analysis.get('recommendations', []))
                        
                        # Experience Gap Analysis
                        st.markdown('<div class="card">', unsafe_allow_html=True)
                        st.subheader("Experience Gap Analysis")
                        experience_gaps = analysis.get('experience_gap_analysis', [])
                        if experience_gaps:
                            for gap in experience_gaps:
                                st.markdown(f"🔸 **{gap}**")
                        else:
                            st.markdown("*No specific experience gaps identified.*")
                        st.markdown('</div>', unsafe_allow_html=True)
                    
                    with analysis_detail_tabs[1]:
                        # Keyword Analysis
                        st.markdown('<div class="card">', unsafe_allow_html=True)
                        keywords = analysis.get('keyword_analysis', [])
                        display_keywords(keywords, max_cols=3)
                        st.markdown('</div>', unsafe_allow_html=True)
                        
                        # Potential Alternative Job Titles
                        st.markdown('<div class="card">', unsafe_allow_html=True)
                        st.subheader("Alternative Job Titles to Consider")
                        alt_titles = analysis.get('potential_job_titles', [])
                        if alt_titles:
                            st.markdown("Based on your CV, you might also be a good fit for these roles:")
                            for title in alt_titles:
                                st.markdown(f"🔹 **{title}**")
                        else:
                            st.markdown("*No alternative job titles suggested.*")
                        st.markdown('</div>', unsafe_allow_html=True)
                    
                    with analysis_detail_tabs[2]:
                        # Generate industry analysis
                        with st.spinner("Generating industry insights..."):
                            # Check if we need to generate industry analysis
                            if not 'industry_analysis' in st.session_state or st.session_state['industry_analysis'] is None:
                                # Generate industry analysis
                                industry_analysis = analyze_industry_fit(
                                    client,
                                    {'parsed_data': analysis_data['cv_parsed_data']}, 
                                    analysis_data['description_text'],
                                    analysis
                                )
                                st.session_state['industry_analysis'] = industry_analysis
                            else:
                                industry_analysis = st.session_state['industry_analysis']
                            
                            if industry_analysis:
                                # Industry overview
                                st.markdown('<div class="card">', unsafe_allow_html=True)
                                industry_col1, industry_col2 = st.columns([1, 1])
                                
                                with industry_col1:
                                    st.subheader("Industry Profile")
                                    st.markdown(f"**Industry:** {industry_analysis.get('industry_identified', 'Unknown')}")
                                    industry_fit = industry_analysis.get('industry_fit_score', 0)
                                    
                                    # Determine colour for industry fit
                                    if industry_fit >= 80:
                                        ind_color = "green"
                                        ind_text = "Strong Industry Fit"
                                    elif industry_fit >= 60:
                                        ind_color = "orange" 
                                        ind_text = "Moderate Industry Fit"
                                    else:
                                        ind_color = "red"
                                        ind_text = "Low Industry Fit"

# === MAIN APPLICATION ===
def main():
    st.write("Application starting...")  # Debug line
    
    # Check for Stripe session_id in URL params for payment completion
    query_params = st.query_params
    if "success" in query_params and "session_id" in query_params:
        session_id = query_params["session_id"]
        
        # Process the successful payment
        if handle_successful_payment(session_id):
            st.success("Subscription activated successfully!")
            
            # Clear URL parameters
            st.query_params.clear()
    
    # Check if we're in admin mode
    admin_mode = False
    if "admin" in st.query_params:
        # Admin authentication
        if auth_manager.check_admin_password():
            admin_mode = True
    
    if admin_mode:
        # Display admin dashboard
        show_admin_page()
    else:
        # Check if user is logged in
        if 'user_id' in st.session_state:
            # Show user dashboard
            show_dashboard()
        else:
            # Show login page
            show_login_page()

if __name__ == "__main__":
    main()
