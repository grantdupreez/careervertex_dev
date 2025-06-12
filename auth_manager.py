import streamlit as st
import uuid
import bcrypt
import hmac
from datetime import datetime

class AuthManager:
    """Manages user authentication and registration."""
    
    def __init__(self, db_manager):
        self.db_manager = db_manager
    
    def register_user(self, email, password, full_name):
        """Register a new user."""
        try:
            # Check if user already exists
            existing_user = self.db_manager.execute_query(
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
            self.db_manager.execute_query(
                """
                INSERT INTO users (user_id, email, password_hash, full_name, created_at)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (user_id, email, password_hash, full_name, datetime.now()),
                fetch=False
            )
            
            return True, str(user_id)
        except Exception as e:
            print(f"Failed to register user: {str(e)}")
            return False, "Registration failed. Please try again."
    
    def login_user(self, email, password):
        """Login a user and return user data if successful."""
        try:
            # Fetch user from database
            user_data = self.db_manager.execute_query(
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
            self.db_manager.execute_query(
                "UPDATE users SET last_login = %s WHERE user_id = %s",
                (datetime.now(), user['user_id']),
                fetch=False
            )
            
            # Return user data
            return True, dict(user)
        except Exception as e:
            print(f"Failed to login user: {str(e)}")
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
        try:
            user_data = self.db_manager.execute_query(
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
                    self.db_manager.execute_query(
                        "UPDATE users SET subscription_status = 'expired' WHERE user_id = %s",
                        (user_id,),
                        fetch=False
                    )
                return False
        except Exception as e:
            print(f"Failed to check subscription: {str(e)}")
            return False
    
    def get_user_data(self, user_id):
        """Get user data by ID."""
        try:
            user_data = self.db_manager.execute_query(
                "SELECT * FROM users WHERE user_id = %s",
                (user_id,)
            )
            
            if not user_data:
                return None
                
            return dict(user_data[0])
        except Exception as e:
            print(f"Failed to get user data: {str(e)}")
            return None
    
    def logout_user(self):
        """Logout the current user."""
        for key in ['user_id', 'user_email', 'user_name', 'user_data']:
            if key in st.session_state:
                del st.session_state[key]