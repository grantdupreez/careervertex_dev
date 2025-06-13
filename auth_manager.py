import streamlit as st
import uuid
import bcrypt
import hmac
from datetime import datetime
import traceback

class AuthManager:
    """Manages user authentication and registration."""
    
    def __init__(self, db_manager):
        self.db_manager = db_manager
    
    def register_user(self, email, password, full_name):
        """Register a new user."""
        # Validate inputs
        if not email or not password:
            return False, "Email and password are required."
        
        if not self.db_manager or not self.db_manager.connection_params:
            return False, "Database connection not available."
        
        try:
            # Check if user already exists
            existing_user = self.db_manager.execute_query(
                "SELECT user_id FROM users WHERE email = %s",
                (email.lower().strip(),)  # Normalize email
            )
            
            if existing_user and len(existing_user) > 0:
                return False, "User with this email already exists."
            
            # Generate user ID
            user_id = str(uuid.uuid4())
            
            # Hash the password
            password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            
            # Insert user into database
            result = self.db_manager.execute_query(
                """
                INSERT INTO users (user_id, email, password_hash, full_name, created_at)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (user_id, email.lower().strip(), password_hash, full_name, datetime.now()),
                fetch=False,
                commit=True
            )
            
            if result:
                # Verify the user was created
                verify_user = self.db_manager.execute_query(
                    "SELECT user_id FROM users WHERE user_id = %s",
                    (user_id,)
                )
                
                if verify_user and len(verify_user) > 0:
                    print(f"User registered successfully: {email}")
                    return True, user_id
                else:
                    print("User creation verification failed")
                    return False, "User creation could not be verified."
            else:
                print("Insert query returned None/False")
                return False, "Failed to create user account."
                
        except psycopg2.IntegrityError as e:
            # Handle specific database constraints
            if "users_email_key" in str(e):
                return False, "Email address already registered."
            else:
                print(f"Integrity error during registration: {str(e)}")
                return False, "Registration failed due to data conflict."
        except Exception as e:
            print(f"Failed to register user: {str(e)}")
            traceback.print_exc()
            return False, f"Registration failed: {str(e)}"
    
    def login_user(self, email, password):
        """Login a user and return user data if successful."""
        # Validate inputs
        if not email or not password:
            return False, "Email and password are required."
        
        if not self.db_manager or not self.db_manager.connection_params:
            return False, "Database connection not available."
        
        try:
            # Fetch user from database
            user_data = self.db_manager.execute_query(
                "SELECT * FROM users WHERE email = %s",
                (email.lower().strip(),)  # Normalize email
            )
            
            if not user_data or len(user_data) == 0:
                return False, "Invalid email or password."
            
            user = user_data[0]
            
            # Check password
            try:
                password_valid = bcrypt.checkpw(
                    password.encode('utf-8'), 
                    user['password_hash'].encode('utf-8')
                )
                
                if not password_valid:
                    return False, "Invalid email or password."
            except Exception as e:
                print(f"Password verification error: {str(e)}")
                return False, "Authentication error. Please try again."
            
            # Update last login time
            self.db_manager.execute_query(
                "UPDATE users SET last_login = %s WHERE user_id = %s",
                (datetime.now(), user['user_id']),
                fetch=False,
                commit=True
            )
            
            # Return user data as dict
            user_dict = dict(user)
            print(f"User logged in successfully: {email}")
            return True, user_dict
            
        except Exception as e:
            print(f"Failed to login user: {str(e)}")
            traceback.print_exc()
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
            if "admin_passwords" in st.secrets and st.session_state["admin_username"] in st.secrets["admin_passwords"]:
                stored_password = st.secrets.admin_passwords[st.session_state["admin_username"]]
                if isinstance(stored_password, (str, bytes)):
                     if hmac.compare_digest(
                        st.session_state["admin_password"],
                        str(stored_password)
                     ):
                        st.session_state["admin_password_correct"] = True
                        del st.session_state["admin_password"]
                        del st.session_state["admin_username"]
                        return
                else:
                     st.error(f"Password configuration error for admin user {st.session_state['admin_username']}.")

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
        if not self.db_manager or not self.db_manager.connection_params:
            print("Database connection not available for subscription check")
            return False
        
        try:
            user_data = self.db_manager.execute_query(
                """
                SELECT subscription_status, subscription_end 
                FROM users 
                WHERE user_id = %s
                """,
                (user_id,)
            )
            
            if not user_data or len(user_data) == 0:
                return False
            
            user = user_data[0]
            
            # Check if subscription is active and not expired
            if user['subscription_status'] == 'active' and user['subscription_end'] and user['subscription_end'] > datetime.now():
                return True
            else:
                # Update status to expired if past end date
                if user['subscription_status'] == 'active' and user['subscription_end'] and user['subscription_end'] <= datetime.now():
                    self.db_manager.execute_query(
                        "UPDATE users SET subscription_status = 'expired' WHERE user_id = %s",
                        (user_id,),
                        fetch=False,
                        commit=True
                    )
                return False
        except Exception as e:
            print(f"Failed to check subscription: {str(e)}")
            traceback.print_exc()
            return False
    
    def get_user_data(self, user_id):
        """Get user data by ID."""
        if not self.db_manager or not self.db_manager.connection_params:
            print("Database connection not available for get_user_data")
            return None
        
        try:
            user_data = self.db_manager.execute_query(
                "SELECT * FROM users WHERE user_id = %s",
                (user_id,)
            )
            
            if not user_data or len(user_data) == 0:
                return None
                
            return dict(user_data[0])
        except Exception as e:
            print(f"Failed to get user data: {str(e)}")
            traceback.print_exc()
            return None
    
    def logout_user(self):
        """Logout the current user."""
        # Clear all user-related session state
        keys_to_remove = ['user_id', 'user_email', 'user_name', 'user_data', 
                         'current_analysis_id', 'selected_cv_id', 'show_analysis_tab']
        
        for key in keys_to_remove:
            if key in st.session_state:
                del st.session_state[key]
        
        print("User logged out successfully")

# Import psycopg2 for exception handling
try:
    import psycopg2
except ImportError:
    # Create a dummy class if psycopg2 is not available
    class psycopg2:
        class IntegrityError(Exception):
            pass
