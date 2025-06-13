import bcrypt
import secrets
from datetime import datetime, timedelta

class AuthManager:
    """Simplified authentication manager."""
    
    def __init__(self, db_manager):
        self.db = db_manager
    
    def hash_password(self, password):
        """Hash a password."""
        return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    def verify_password(self, password, password_hash):
        """Verify a password against its hash."""
        return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))
    
    def register_user(self, email, password, full_name):
        """Register a new user."""
        # Check if user exists
        if self.db.get_user_by_email(email):
            return None, "Email already registered"
        
        # Create user
        password_hash = self.hash_password(password)
        user_id = self.db.create_user(email, password_hash, full_name)
        
        if user_id:
            return user_id, "Registration successful"
        return None, "Registration failed"
    
    def login_user(self, email, password):
        """Login user with email and password."""
        user = self.db.get_user_by_email(email)
        
        if not user:
            return None, "Invalid email or password"
        
        if not self.verify_password(password, user['password_hash']):
            return None, "Invalid email or password"
        
        return user, "Login successful"
    
    def generate_login_token(self, user_id):
        """Generate a secure login token for email authentication."""
        token = secrets.token_urlsafe(32)
        expires = datetime.now() + timedelta(hours=24)
        
        if self.db.set_login_token(user_id, token, expires):
            return token
        return None
    
    def verify_login_token(self, token):
        """Verify and consume a login token."""
        return self.db.get_user_by_token(token)
    
    def check_subscription(self, user_id):
        """Check if user has active subscription."""
        user = self.db.get_user_by_id(user_id)
        if not user:
            return False
        
        if user['subscription_status'] == 'active' and user['subscription_end']:
            return user['subscription_end'] > datetime.now()
        
        return False
