import streamlit as st
from datetime import datetime

# --- Error Message Constants ---
ERROR_MESSAGES = {
    "api_timeout": "The API request timed out. This could be due to high server load or a complex resume. Please try again.",
    "api_error": "There was an error communicating with the AI service. Please try again later.",
    "parse_error": "There was an error parsing your document. Please check file format and try again.",
    "json_error": "There was an error processing the response data. Please try again."
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
                st.info("If this problem persists, try uploading a different file format or simplify your resume.")

# Global error tracker instance
error_tracker = ErrorTracker()
