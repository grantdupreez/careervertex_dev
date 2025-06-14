import streamlit as st
import psycopg2
from psycopg2.extras import Json, DictCursor
import uuid
from datetime import datetime
import traceback

class DatabaseManager:
    """Simplified database manager for CareerVertex."""
    
    def __init__(self):
        # Test connection on initialization
        try:
            test_conn = self.get_connection()
            if test_conn:
                test_conn.close()
        except Exception as e:
            print(f"Database initialization error: {e}")
    
    def get_connection(self):
        """Get a database connection."""
        try:
            # Use the simple connection method that works in test files
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
            print(f"Database connection error: {e}")
            traceback.print_exc()
            return None
    
    def execute(self, query, params=None, fetch=True):
        """Execute a database query."""
        conn = self.get_connection()
        if not conn:
            print(f"Failed to get connection for query: {query[:50]}...")
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
            print(f"Query: {query[:100]}...")
            if params:
                print(f"Params: {params}")
            traceback.print_exc()
            
            # Return None instead of raising to match debug behavior
            return None
        finally:
            conn.close()
    
    def table_exists(self, table_name):
        """Check if a table exists."""
        query = """
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = %s
            )
        """
        result = self.execute(query, (table_name,))
        return result[0]['exists'] if result else False
    
    def get_existing_tables(self):
        """Get list of existing tables in the database."""
        query = """
            SELECT tablename FROM pg_tables 
            WHERE schemaname = 'public'
        """
        result = self.execute(query)
        if result:
            return [row['tablename'] for row in result]
        return []
    
    def create_tables_if_needed(self):
        """Create tables if they don't exist - simplified version."""
        tables_created = 0
        tables_checked = 0
        
        # Define tables in order of dependency
        table_definitions = [
            ('users', """
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
                    last_login TIMESTAMP,
                    login_token VARCHAR(255),
                    token_expires TIMESTAMP
                )
            """),
            ('cvs', """
                CREATE TABLE IF NOT EXISTS cvs (
                    cv_id UUID PRIMARY KEY,
                    user_id UUID REFERENCES users(user_id) ON DELETE CASCADE,
                    cv_name VARCHAR(255) NOT NULL,
                    cv_text TEXT,
                    parsed_data JSONB,
                    uploaded_at TIMESTAMP DEFAULT NOW()
                )
            """),
            ('analyses', """
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
            """),
            ('payments', """
                CREATE TABLE IF NOT EXISTS payments (
                    payment_id UUID PRIMARY KEY,
                    user_id UUID REFERENCES users(user_id) ON DELETE CASCADE,
                    stripe_session_id VARCHAR(255),
                    amount DECIMAL(10, 2),
                    status VARCHAR(50),
                    created_at TIMESTAMP DEFAULT NOW()
                )
            """),
            # Also create job_descriptions and token_usage tables that might be referenced
            ('job_descriptions', """
                CREATE TABLE IF NOT EXISTS job_descriptions (
                    job_id UUID PRIMARY KEY,
                    user_id UUID REFERENCES users(user_id) ON DELETE CASCADE,
                    job_title VARCHAR(255),
                    company VARCHAR(255),
                    job_description TEXT,
                    parsed_data JSONB,
                    created_at TIMESTAMP DEFAULT NOW()
                )
            """),
            ('token_usage', """
                CREATE TABLE IF NOT EXISTS token_usage (
                    usage_id UUID PRIMARY KEY,
                    user_id UUID REFERENCES users(user_id) ON DELETE CASCADE,
                    tokens_used INTEGER,
                    operation VARCHAR(50),
                    created_at TIMESTAMP DEFAULT NOW()
                )
            """)
        ]
        
        # Create each table
        for table_name, create_query in table_definitions:
            tables_checked += 1
            
            # Check if table exists first
            if not self.table_exists(table_name):
                print(f"Creating table: {table_name}")
                result = self.execute(create_query, fetch=False)
                if result is not None:
                    tables_created += 1
                    print(f"✓ Created table: {table_name}")
                else:
                    print(f"✗ Failed to create table: {table_name}")
            else:
                print(f"✓ Table already exists: {table_name}")
        
        # Create indexes
        index_queries = [
            "CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)",
            "CREATE INDEX IF NOT EXISTS idx_users_token ON users(login_token)",
            "CREATE INDEX IF NOT EXISTS idx_analyses_user ON analyses(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_cvs_user ON cvs(user_id)"
        ]
        
        for index_query in index_queries:
            self.execute(index_query, fetch=False)
        
        # Add missing columns to existing tables
        self._add_missing_columns()
        
        return tables_created, tables_checked
    
    def _add_missing_columns(self):
        """Add missing columns to existing tables."""
        # Check and add missing columns to users table
        user_columns = [
            ('last_login', 'ALTER TABLE users ADD COLUMN IF NOT EXISTS last_login TIMESTAMP'),
            ('subscription_start', 'ALTER TABLE users ADD COLUMN IF NOT EXISTS subscription_start TIMESTAMP'),
            ('stripe_subscription_id', 'ALTER TABLE users ADD COLUMN IF NOT EXISTS stripe_subscription_id VARCHAR(255)')
        ]
        
        for column_name, alter_query in user_columns:
            try:
                # PostgreSQL 9.6+ supports IF NOT EXISTS
                self.execute(alter_query, fetch=False)
                print(f"✓ Ensured column {column_name} exists")
            except Exception as e:
                # For older PostgreSQL versions, check if column exists first
                try:
                    check_query = """
                        SELECT column_name 
                        FROM information_schema.columns 
                        WHERE table_name = 'users' AND column_name = %s
                    """
                    exists = self.execute(check_query, (column_name,))
                    if not exists:
                        # Try without IF NOT EXISTS
                        simple_query = alter_query.replace(' IF NOT EXISTS', '')
                        self.execute(simple_query, fetch=False)
                        print(f"✓ Added column {column_name}")
                except Exception as e2:
                    print(f"Could not add column {column_name}: {e2}")
    
    def initialize_schema(self):
        """Initialize database schema - wrapper for compatibility."""
        tables_created, tables_checked = self.create_tables_if_needed()
        # Return True if all tables exist (either created or already existed)
        existing_tables = self.get_existing_tables()
        required_tables = ['users', 'cvs', 'analyses', 'payments']
        return all(table in existing_tables for table in required_tables)
    
    # User operations
    def create_user(self, email, password_hash, full_name):
        """Create a new user."""
        user_id = str(uuid.uuid4())
        query = """
            INSERT INTO users (user_id, email, password_hash, full_name, created_at)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING user_id
        """
        result = self.execute(query, (user_id, email.lower(), password_hash, full_name, datetime.now()))
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
        # First check if subscription_start column exists
        columns_query = """
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'users' AND column_name = 'subscription_start'
        """
        has_start_column = self.execute(columns_query)
        
        if has_start_column:
            query = """
                UPDATE users 
                SET subscription_status = %s, 
                    subscription_end = %s,
                    stripe_customer_id = %s,
                    subscription_start = CASE 
                        WHEN subscription_start IS NULL THEN NOW() 
                        ELSE subscription_start 
                    END
                WHERE user_id = %s
            """
        else:
            # Simpler query without subscription_start
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
