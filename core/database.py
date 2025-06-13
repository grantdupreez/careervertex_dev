import streamlit as st
import psycopg2
from psycopg2.extras import Json, DictCursor
import uuid
from datetime import datetime

class DatabaseManager:
    """Simplified database manager for CareerVertex."""
    
    def __init__(self):
        self.connection_params = self._get_connection_params()
    
    def _get_connection_params(self):
        """Get database connection parameters from Streamlit secrets."""
        try:
            return {
                'dbname': st.secrets["DB_NAME"],
                'user': st.secrets["DB_USER"],
                'password': st.secrets["DB_PASSWORD"],
                'host': st.secrets["DB_HOST"],
                'port': st.secrets["DB_PORT"],
                'sslmode': 'require'
            }
        except KeyError as e:
            st.error(f"Missing database configuration: {e}")
            return None
    
    def get_connection(self):
        """Get a database connection."""
        if not self.connection_params:
            return None
        try:
            return psycopg2.connect(**self.connection_params)
        except Exception as e:
            print(f"Database connection error: {e}")
            return None
    
    def execute(self, query, params=None, fetch=True):
        """Execute a database query."""
        conn = self.get_connection()
        if not conn:
            return None
        
        try:
            with conn.cursor(cursor_factory=DictCursor) as cur:
                cur.execute(query, params)
                
                if fetch:
                    result = cur.fetchall()
                else:
                    result = cur.rowcount
                
                conn.commit()
                return result
        except Exception as e:
            conn.rollback()
            print(f"Query error: {e}")
            return None
        finally:
            conn.close()
    
    def initialize_schema(self):
        """Initialize database schema."""
        schema_queries = [
            # Users table
            """
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
            # CVs table
            """
            CREATE TABLE IF NOT EXISTS cvs (
                cv_id UUID PRIMARY KEY,
                user_id UUID REFERENCES users(user_id) ON DELETE CASCADE,
                cv_name VARCHAR(255) NOT NULL,
                cv_text TEXT,
                parsed_data JSONB,
                uploaded_at TIMESTAMP DEFAULT NOW()
            )
            """,
            # Analyses table
            """
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
            # Payments table
            """
            CREATE TABLE IF NOT EXISTS payments (
                payment_id UUID PRIMARY KEY,
                user_id UUID REFERENCES users(user_id) ON DELETE CASCADE,
                stripe_session_id VARCHAR(255),
                amount DECIMAL(10, 2),
                status VARCHAR(50),
                created_at TIMESTAMP DEFAULT NOW()
            )
            """,
            # Create indexes
            "CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)",
            "CREATE INDEX IF NOT EXISTS idx_users_token ON users(login_token)",
            "CREATE INDEX IF NOT EXISTS idx_analyses_user ON analyses(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_cvs_user ON cvs(user_id)"
        ]
        
        for query in schema_queries:
            result = self.execute(query, fetch=False)
            if result is None:
                return False
        
        return True
    
    # User operations
    def create_user(self, email, password_hash, full_name):
        """Create a new user."""
        user_id = str(uuid.uuid4())
        query = """
            INSERT INTO users (user_id, email, password_hash, full_name)
            VALUES (%s, %s, %s, %s)
            RETURNING user_id
        """
        result = self.execute(query, (user_id, email.lower(), password_hash, full_name))
        return result[0]['user_id'] if result else None
    
    def get_user_by_email(self, email):
        """Get user by email."""
        query = "SELECT * FROM users WHERE email = %s"
        result = self.execute(query, (email.lower(),))
        return dict(result[0]) if result else None
    
    def get_user_by_id(self, user_id):
        """Get user by ID."""
        query = "SELECT * FROM users WHERE user_id = %s"
        result = self.execute(query, (user_id,))
        return dict(result[0]) if result else None
    
    def update_user_subscription(self, user_id, status, end_date, stripe_customer_id):
        """Update user subscription status."""
        query = """
            UPDATE users 
            SET subscription_status = %s, 
                subscription_end = %s,
                stripe_customer_id = %s
            WHERE user_id = %s
        """
        return self.execute(query, (status, end_date, stripe_customer_id, user_id), fetch=False)
    
    def set_login_token(self, user_id, token, expires):
        """Set login token for email authentication."""
        query = """
            UPDATE users 
            SET login_token = %s, token_expires = %s
            WHERE user_id = %s
        """
        return self.execute(query, (token, expires, user_id), fetch=False)
    
    def get_user_by_token(self, token):
        """Get user by login token."""
        query = """
            SELECT * FROM users 
            WHERE login_token = %s AND token_expires > NOW()
        """
        result = self.execute(query, (token,))
        if result:
            # Clear the token after use
            self.execute(
                "UPDATE users SET login_token = NULL, token_expires = NULL WHERE user_id = %s",
                (result[0]['user_id'],),
                fetch=False
            )
        return dict(result[0]) if result else None
    
    # CV operations
    def save_cv(self, user_id, cv_name, cv_text, parsed_data=None):
        """Save a CV."""
        cv_id = str(uuid.uuid4())
        query = """
            INSERT INTO cvs (cv_id, user_id, cv_name, cv_text, parsed_data)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING cv_id
        """
        result = self.execute(query, (cv_id, user_id, cv_name, cv_text, Json(parsed_data)))
        return result[0]['cv_id'] if result else None
    
    def update_cv_parsed_data(self, cv_id, parsed_data):
        """Update CV parsed data."""
        query = "UPDATE cvs SET parsed_data = %s WHERE cv_id = %s"
        return self.execute(query, (Json(parsed_data), cv_id), fetch=False)
    
    def get_user_cvs(self, user_id):
        """Get all CVs for a user."""
        query = "SELECT * FROM cvs WHERE user_id = %s ORDER BY uploaded_at DESC"
        result = self.execute(query, (user_id,))
        return [dict(cv) for cv in result] if result else []
    
    def get_cv_by_id(self, cv_id):
        """Get CV by ID."""
        query = "SELECT * FROM cvs WHERE cv_id = %s"
        result = self.execute(query, (cv_id,))
        return dict(result[0]) if result else None
    
    def delete_cv(self, cv_id):
        """Delete a CV."""
        query = "DELETE FROM cvs WHERE cv_id = %s"
        return self.execute(query, (cv_id,), fetch=False)
    
    # Analysis operations
    def save_analysis(self, user_id, cv_id, job_title, company, job_description, parsed_job, analysis_result):
        """Save an analysis."""
        analysis_id = str(uuid.uuid4())
        query = """
            INSERT INTO analyses 
            (analysis_id, user_id, cv_id, job_title, company, job_description, parsed_job, analysis_result)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING analysis_id
        """
        result = self.execute(
            query,
            (analysis_id, user_id, cv_id, job_title, company, job_description, 
             Json(parsed_job), Json(analysis_result))
        )
        return result[0]['analysis_id'] if result else None
    
    def get_user_analyses(self, user_id):
        """Get all analyses for a user."""
        query = """
            SELECT a.*, c.cv_name 
            FROM analyses a
            JOIN cvs c ON a.cv_id = c.cv_id
            WHERE a.user_id = %s 
            ORDER BY a.created_at DESC
        """
        result = self.execute(query, (user_id,))
        return [dict(analysis) for analysis in result] if result else []
    
    def get_analysis_by_id(self, analysis_id):
        """Get analysis by ID."""
        query = """
            SELECT a.*, c.cv_name, c.parsed_data as cv_data
            FROM analyses a
            JOIN cvs c ON a.cv_id = c.cv_id
            WHERE a.analysis_id = %s
        """
        result = self.execute(query, (analysis_id,))
        return dict(result[0]) if result else None
    
    # Payment operations
    def save_payment(self, user_id, stripe_session_id, amount, status):
        """Save payment record."""
        payment_id = str(uuid.uuid4())
        query = """
            INSERT INTO payments (payment_id, user_id, stripe_session_id, amount, status)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING payment_id
        """
        result = self.execute(query, (payment_id, user_id, stripe_session_id, amount, status))
        return result[0]['payment_id'] if result else None
