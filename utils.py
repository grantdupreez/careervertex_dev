import io
import re
import json
from PyPDF2 import PdfReader
import docx
from datetime import datetime

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
            print(f"CRITICAL ERROR: {error_type} - {message}")
            if details:
                print(f"Details: {details}")
    
    def get_user_message(self, error_type):
        """Get a user-friendly error message"""
        return ERROR_MESSAGES.get(error_type, "An unexpected error occurred. Please try again.")
    
    def display_errors(self):
        """Display errors in the Streamlit UI if they exist"""
        import streamlit as st
        
        if not self.errors:
            return
        
        with st.expander("Troubleshooting Information", expanded=self.has_critical_error):
            for error in self.errors:
                if error["critical"]:
                    st.markdown(f'<div class="custom-error"><strong>Error:</strong> {error["message"]}</div>', unsafe_allow_html=True)
                else:
                    st.markdown(f'<div class="custom-warning"><strong>Warning:</strong> {error["message"]}</div>', unsafe_allow_html=True)
                
                if error.get("details") and st.checkbox("Show technical details"):
                    st.code(error["details"])
            
            if self.has_critical_error:
                st.info("If this problem persists, try uploading a different file format or simplify your CV.")

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
        print(f"Error reading PDF {file.name}: {str(e)}")
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
        print(f"Error reading DOCX {file.name}: {str(e)}")
        return ""

def extract_text_from_file(file, error_tracker=None):
    """Extract text from a supported file format (PDF, DOCX, TXT)."""
    file_name = file.name.lower()
    try:
        file_content = file.read()
        file.seek(0)
    except Exception as e:
        if error_tracker:
            error_tracker.add_error("parse_error", f"Error reading file {file.name}", True, str(e))
        return None

    if file_name.endswith('.pdf'):
        return extract_text_from_pdf(file)
    elif file_name.endswith('.docx'):
        return extract_text_from_docx(io.BytesIO(file_content))
    elif file_name.endswith('.txt'):
        try:
            return file_content.decode('utf-8')
        except UnicodeDecodeError:
            try:
                return file_content.decode('latin-1')
            except Exception as e:
                if error_tracker:
                    error_tracker.add_error("parse_error", f"Error decoding text file {file.name}", True, str(e))
                return None
    else:
        if error_tracker:
            error_tracker.add_error("parse_error", f"Unsupported file type: {file_name}", False)
        return None

# === JSON PARSING UTILITIES ===
def extract_json_from_string(text, default_structure=None):
    """
    Extracts JSON object from a string with multiple fallback strategies.
    Returns extracted JSON string or default_structure if all extraction methods fail.
    """
    if not text:
        return default_structure
    
    # Strategy 1: Look for JSON within ```json ... ``` markdown fences
    json_pattern = r'```(?:json)?\s*(\{.*\}|\[.*\])\s*```'
    match = re.search(json_pattern, text, re.DOTALL | re.IGNORECASE)
    if match:
        potential_json = match.group(1).strip()
        try:
            parsed = json.loads(potential_json)
            return json.dumps(parsed)
        except json.JSONDecodeError:
            pass
    
    # Strategy 2: Check if entire text is valid JSON
    try:
        parsed = json.loads(text.strip())
        return json.dumps(parsed)
    except json.JSONDecodeError:
        pass
        
    # Strategy 3: Find the first occurrence of what looks like a JSON object/array
    bracket_pattern = r'(\{.*\}|\[.*\])'
    match = re.search(bracket_pattern, text, re.DOTALL)
    if match:
        potential_json = match.group(0).strip()
        try:
            parsed = json.loads(potential_json)
            return json.dumps(parsed)
        except json.JSONDecodeError:
            pass
    
    # Strategy 4: Try to extract JSON by finding matching braces
    cleaned_text = text.strip()
    start_brace = cleaned_text.find('{')
    start_bracket = cleaned_text.find('[')
    end_brace = cleaned_text.rfind('}')
    end_bracket = cleaned_text.rfind(']')
    
    if start_brace >= 0 and end_brace >= 0 and (start_bracket < 0 or start_brace < start_bracket):
        potential_json = cleaned_text[start_brace:end_brace+1]
    elif start_bracket >= 0 and end_bracket >= 0:
        potential_json = cleaned_text[start_bracket:end_bracket+1]
    else:
        return default_structure
    
    try:
        parsed = json.loads(potential_json)
        return json.dumps(parsed)
    except json.JSONDecodeError:
        return default_structure