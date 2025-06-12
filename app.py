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
        self.db_config = None
        self._connection_test_passed = False
        
        # Initialize database configuration
        try:
            # Check for required secrets
            required_db_secrets = ["DB_NAME", "DB_USER", "DB_PASSWORD", "DB_HOST", "DB_PORT"]
            for secret in required_db_secrets:
                if secret not in st.secrets:
                    st.error(f"Missing required database secret: {secret}")
                    print(f"Missing required database secret: {secret}")
                    return

            # Store configuration without creating connection pool yet
            self.db_config = {
                'dbname': st.secrets["DB_NAME"],
                'user': st.secrets["DB_USER"],
                'password': st.secrets["DB_PASSWORD"],
                'host': st.secrets["DB_HOST"],
                'port': st.secrets["DB_PORT"],
                'sslmode': 'require',
                'connect_timeout': 10  # 10 second timeout
            }
            
            # Test connection first
            self._test_connection()
            
        except Exception as e:
            error_tracker.add_error("db_error", "Failed to initialize database configuration", True, str(e))
            st.error(f"❌ Database configuration failed: {str(e)}")
            print(f"Database configuration error: {str(e)}")
            self.db_config = None
    
    def _test_connection(self):
        """Test a single database connection before initializing pool."""
        if not self.db_config:
            return False
            
        try:
            # Test with a simple connection
            test_conn = psycopg2.connect(**self.db_config)
            
            # Test a simple query
            with test_conn.cursor() as cur:
                cur.execute("SELECT 1")
                result = cur.fetchone()
                
            test_conn.close()
            
            if result and result[0] == 1:
                self._connection_test_passed = True
                print("✅ Database connection test passed")
                st.success("✅ Connected to Google Cloud SQL database")
                return True
            else:
                raise Exception("Connection test query failed")
                
        except Exception as e:
            error_tracker.add_error("db_error", f"Database connection test failed: {str(e)}", True, str(e))
            st.error(f"❌ Database connection test failed: {str(e)}")
            print(f"Database connection test error: {str(e)}")
            return False
    
    def get_connection(self):
        """Get a direct database connection."""
        if not self.db_config or not self._connection_test_passed:
            error_tracker.add_error("db_error", "No valid database configuration available", True)
            return None
            
        try:
            return psycopg2.connect(**self.db_config)
        except Exception as e:
            error_tracker.add_error("db_error", f"Failed to get database connection: {str(e)}", True, str(e))
            return None
    
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
            error_tracker.add_error("db_error", f"Database query execution failed: {str(e)}", True, str(e))
            return None
        finally:
            if conn:
                conn.close()
    
    def initialize_schema(self):
        """Initialize the database schema if it doesn't exist."""
        if not self._connection_test_passed:
            print("Skipping schema initialization - no valid database connection")
            return
            
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
            try:
                self.execute_query(query, fetch=False)
            except Exception as e:
                print(f"Error creating schema: {str(e)}")
                break
            
        print("Database schema initialization completed")

# Initialize database manager
db_manager = DatabaseManager()

# Make sure schema is initialized
if db_manager._connection_test_passed:
    db_manager.initialize_schema()
else:
    st.warning("⚠️ Database connection failed. Some features may not work properly.")

# === STRIPE INTEGRATION ===
# Initialize Stripe with API key
if "STRIPE_SECRET_KEY" in st.secrets:
    stripe.api_key = st.secrets["STRIPE_SECRET_KEY"]
else:
    st.warning("⚠️ Stripe not configured. Payment features will not work.")

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
        if not db_manager._connection_test_passed:
            return False, "Database connection not available. Please try again later."
            
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
        if not db_manager._connection_test_passed:
            return False, "Database connection not available. Please try again later."
            
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
        if not db_manager._connection_test_passed:
            return False
            
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
        if not db_manager._connection_test_passed:
            return None
            
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

# [The rest of the code remains the same - all the text extraction, API utilities, 
# analysis functions, UI components, and page functions stay identical...]

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

# [Include all the remaining functions here - API utilities, CV management, UI components, analysis functions, and pages]
# [For brevity, I'm truncating this, but in the actual implementation, all functions should be included]

# === MAIN APPLICATION ===
def main():
    st.write("Application starting...")  # Debug line
    
    # Check for database connection before proceeding
    if not db_manager._connection_test_passed:
        st.error("❌ Database connection failed. Please check your configuration and try again.")
        st.info("The application requires a working database connection to function properly.")
        
        # Show basic connection troubleshooting
        with st.expander("Connection Troubleshooting"):
            st.markdown("""
            **Common issues:**
            1. **Network connectivity**: Check if the database server is reachable
            2. **Firewall rules**: Ensure your IP is allowed to connect
            3. **SSL requirements**: Google Cloud SQL requires SSL connections
            4. **Credentials**: Verify username, password, and database name
            5. **Connection limits**: Database may have reached connection limit
            
            **Current status:**
            - Database configuration: ✅ Loaded
            - Connection test: ❌ Failed
            """)
        return
    
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

# [Include all the remaining function definitions here]

if __name__ == "__main__":
    main()
