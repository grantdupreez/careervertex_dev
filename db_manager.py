import streamlit as st
import psycopg2
from psycopg2.extras import Json, DictCursor
import uuid
from datetime import datetime
import time

class DatabaseManager:
    """Manages database connections and operations."""
    
    def __init__(self):
        self.connection_params = None
        self._connection = None
        
        # Initialize connection parameters
        try:
            # Check for required secrets
            required_db_secrets = ["DB_NAME", "DB_USER", "DB_PASSWORD", "DB_HOST", "DB_PORT"]
            missing_secrets = []
            
            for secret in required_db_secrets:
                if secret not in st.secrets:
                    missing_secrets.append(secret)
            
            if missing_secrets:
                st.error(f"Missing required database secrets: {', '.join(missing_secrets)}")
                print(f"Missing required database secrets: {', '.join(missing_secrets)}")
                return

            # Store connection parameters
            self.connection_params = {
                'dbname': st.secrets["DB_NAME"],
                'user': st.secrets["DB_USER"],
                'password': st.secrets["DB_PASSWORD"],
                'host': st.secrets["DB_HOST"],
                'port': st.secrets["DB_PORT"],
                'sslmode': 'require',
                'connect_timeout': 10
            }
            
            print("Database connection parameters configured successfully")
        except Exception as e:
            st.error(f"❌ Database connection configuration failed: {str(e)}")
            print(f"Database connection error: {str(e)}")
            self.connection_params = None
    
    def get_connection(self, retry_count=3):
        """Get a new database connection with retry logic."""
        if not self.connection_params:
            print("No connection parameters available")
            return None
        
        last_error = None
        for attempt in range(retry_count):
            try:
                # Always create a fresh connection
                conn = psycopg2.connect(**self.connection_params)
                # Set autocommit to False to ensure we control transactions
                conn.autocommit = False
                return conn
            except psycopg2.OperationalError as e:
                last_error = e
                print(f"Connection attempt {attempt + 1} failed: {str(e)}")
                if attempt < retry_count - 1:
                    time.sleep(0.5 * (attempt + 1))  # Exponential backoff
            except Exception as e:
                print(f"Unexpected error getting connection: {str(e)}")
                return None
        
        print(f"Failed to get database connection after {retry_count} attempts: {str(last_error)}")
        return None
    
    def execute_query(self, query, params=None, fetch=True, commit=True):
        """Execute a database query with proper connection management."""
        conn = None
        cursor = None
        result = None
        
        try:
            # Get a fresh connection for each query
            conn = self.get_connection()
            if not conn:
                print("Failed to get database connection")
                return None
            
            # Create cursor with DictCursor for dictionary results
            cursor = conn.cursor(cursor_factory=DictCursor)
            
            # Execute the query
            cursor.execute(query, params)
            
            # Fetch results if requested
            if fetch:
                result = cursor.fetchall()
            else:
                # For non-fetch queries, return True to indicate success
                result = True
            
            # Commit if requested and query was successful
            if commit and not fetch:
                conn.commit()
            elif commit and fetch and query.strip().upper().startswith(('INSERT', 'UPDATE', 'DELETE')):
                # Also commit for INSERT/UPDATE/DELETE queries that return data (RETURNING clause)
                conn.commit()
            
            return result
            
        except psycopg2.IntegrityError as e:
            if conn:
                conn.rollback()
            print(f"Database integrity error: {str(e)}")
            print(f"Query: {query}")
            print(f"Params: {params}")
            raise  # Re-raise integrity errors so the app can handle them
        except psycopg2.Error as e:
            if conn:
                conn.rollback()
            print(f"Database error: {str(e)}")
            print(f"Query: {query}")
            print(f"Params: {params}")
            return None
        except Exception as e:
            if conn:
                conn.rollback()
            print(f"Unexpected error during query execution: {str(e)}")
            print(f"Query: {query}")
            print(f"Params: {params}")
            import traceback
            traceback.print_exc()
            return None
        finally:
            # Always close cursor and connection
            if cursor:
                cursor.close()
            if conn:
                try:
                    conn.close()
                except:
                    pass
    
    def test_connection(self):
        """Test the database connection."""
        try:
            result = self.execute_query("SELECT 1 as test")
            return result is not None and len(result) > 0
        except Exception:
            return False
    
    def initialize_schema(self):
        """Initialize the database schema if it doesn't exist."""
        if not self.connection_params:
            print("Cannot initialize schema: no connection parameters")
            return False
        
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
            """,
            """
            CREATE TABLE IF NOT EXISTS payment_sessions (
                session_id UUID PRIMARY KEY,
                user_id UUID REFERENCES users(user_id),
                stripe_session_id VARCHAR(255) UNIQUE,
                session_data JSONB,
                status VARCHAR(50) DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT NOW(),
                expires_at TIMESTAMP,
                completed_at TIMESTAMP
            )
            """,
            """
            CREATE INDEX IF NOT EXISTS idx_payment_sessions_stripe_id ON payment_sessions(stripe_session_id)
            """,
            """
            CREATE INDEX IF NOT EXISTS idx_payment_sessions_expires ON payment_sessions(expires_at)
            """
        ]
        
        success_count = 0
        for i, query in enumerate(schema_queries):
            try:
                result = self.execute_query(query, fetch=False, commit=True)
                if result:
                    success_count += 1
                    print(f"Schema step {i+1}/{len(schema_queries)} completed")
                else:
                    print(f"Schema step {i+1}/{len(schema_queries)} failed")
            except Exception as e:
                print(f"Error in schema step {i+1}: {str(e)}")
        
        print(f"Database schema initialization completed: {success_count}/{len(schema_queries)} successful")
        return success_count == len(schema_queries)

# CV and Job Description Management Functions
def save_cv(db_manager, user_id, cv_name, cv_text):
    """Save a CV to the database."""
    if not db_manager or not db_manager.connection_params:
        print("Database manager not properly initialized")
        return False, None
    
    try:
        # Check if user already has a CV with this name
        existing_cv = db_manager.execute_query(
            "SELECT cv_id FROM cvs WHERE user_id = %s AND cv_name = %s",
            (user_id, cv_name)
        )
        
        if existing_cv and len(existing_cv) > 0:
            # Update existing CV
            cv_id = existing_cv[0]['cv_id']
            result = db_manager.execute_query(
                """
                UPDATE cvs 
                SET cv_text = %s, upload_date = %s, parsed_data = NULL
                WHERE user_id = %s AND cv_name = %s
                """,
                (cv_text, datetime.now(), user_id, cv_name),
                fetch=False,
                commit=True
            )
            
            if result:
                return True, cv_id
            else:
                return False, None
        else:
            # Create new CV
            cv_id = str(uuid.uuid4())
            result = db_manager.execute_query(
                """
                INSERT INTO cvs (cv_id, user_id, cv_name, cv_text, upload_date)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (cv_id, user_id, cv_name, cv_text, datetime.now()),
                fetch=False,
                commit=True
            )
            
            if result:
                return True, cv_id
            else:
                return False, None
    except Exception as e:
        print(f"Failed to save CV: {str(e)}")
        import traceback
        traceback.print_exc()
        return False, None

def get_user_cvs(db_manager, user_id):
    """Get all CVs for a user."""
    if not db_manager or not db_manager.connection_params:
        print("Database manager not properly initialized")
        return []
    
    try:
        cvs = db_manager.execute_query(
            "SELECT * FROM cvs WHERE user_id = %s ORDER BY upload_date DESC",
            (user_id,)
        )
        
        if not cvs:
            return []
            
        return [dict(cv) for cv in cvs]
    except Exception as e:
        print(f"Failed to get user CVs: {str(e)}")
        import traceback
        traceback.print_exc()
        return []

def get_cv_by_id(db_manager, cv_id):
    """Get a CV by ID."""
    if not db_manager or not db_manager.connection_params:
        print("Database manager not properly initialized")
        return None
    
    try:
        cv_data = db_manager.execute_query(
            "SELECT * FROM cvs WHERE cv_id = %s",
            (cv_id,)
        )
        
        if not cv_data or len(cv_data) == 0:
            return None
            
        return dict(cv_data[0])
    except Exception as e:
        print(f"Failed to get CV by ID: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

def save_job_description(db_manager, user_id, job_title, company, description_text):
    """Save a job description to the database."""
    if not db_manager or not db_manager.connection_params:
        print("Database manager not properly initialized")
        return False, None
    
    try:
        job_description_id = str(uuid.uuid4())
        result = db_manager.execute_query(
            """
            INSERT INTO job_descriptions 
            (job_description_id, user_id, job_title, company, description_text)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (job_description_id, user_id, job_title, company, description_text),
            fetch=False,
            commit=True
        )
        
        if result:
            return True, job_description_id
        else:
            return False, None
    except Exception as e:
        print(f"Failed to save job description: {str(e)}")
        import traceback
        traceback.print_exc()
        return False, None

def save_analysis_result(db_manager, user_id, cv_id, job_description_id, match_score, analysis_data):
    """Save analysis result to the database."""
    if not db_manager or not db_manager.connection_params:
        print("Database manager not properly initialized")
        return False, None
    
    try:
        analysis_id = str(uuid.uuid4())
        result = db_manager.execute_query(
            """
            INSERT INTO analyses 
            (analysis_id, user_id, cv_id, job_description_id, match_score, analysis_data)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (analysis_id, user_id, cv_id, job_description_id, match_score, Json(analysis_data)),
            fetch=False,
            commit=True
        )
        
        if result:
            return True, analysis_id
        else:
            return False, None
    except Exception as e:
        print(f"Failed to save analysis result: {str(e)}")
        import traceback
        traceback.print_exc()
        return False, None

def get_user_analyses(db_manager, user_id):
    """Get all analyses for a user."""
    if not db_manager or not db_manager.connection_params:
        print("Database manager not properly initialized")
        return []
    
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
        print(f"Failed to get user analyses: {str(e)}")
        import traceback
        traceback.print_exc()
        return []

def get_analysis_by_id(db_manager, analysis_id):
    """Get an analysis by ID."""
    if not db_manager or not db_manager.connection_params:
        print("Database manager not properly initialized")
        return None
    
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
        
        if not analysis_data or len(analysis_data) == 0:
            return None
            
        return dict(analysis_data[0])
    except Exception as e:
        print(f"Failed to get analysis by ID: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

def update_cv_parsed_data(db_manager, cv_id, parsed_data):
    """Update the parsed data for a CV."""
    if not db_manager or not db_manager.connection_params:
        print("Database manager not properly initialized")
        return False
    
    try:
        result = db_manager.execute_query(
            "UPDATE cvs SET parsed_data = %s WHERE cv_id = %s",
            (Json(parsed_data), cv_id),
            fetch=False,
            commit=True
        )
        return result is not None
    except Exception as e:
        print(f"Failed to update CV parsed data: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def log_token_usage(db_manager, user_id, request_type, tokens_used):
    """Log token usage to the database."""
    if not db_manager or not db_manager.connection_params:
        print("Database manager not properly initialized")
        return False
    
    try:
        usage_id = str(uuid.uuid4())
        result = db_manager.execute_query(
            """
            INSERT INTO token_usage (usage_id, user_id, request_type, tokens_used)
            VALUES (%s, %s, %s, %s)
            """,
            (usage_id, user_id, request_type, tokens_used),
            fetch=False,
            commit=True
        )
        return result is not None
    except Exception as e:
        print(f"Failed to log token usage: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
