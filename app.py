import streamlit as st
import pandas as pd
import altair as alt
import numpy as np
import io
import json
import time
import traceback
import hmac
import re
from datetime import datetime
from functools import lru_cache
from PyPDF2 import PdfReader
import docx
import anthropic

# === APP CONFIGURATION ===
st.set_page_config(
    page_title="CareerVertex - Resume Job Match Analyser",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# === THEME SETTINGS AND CUSTOM CSS ===
# Setup color variables for light/dark mode
# These will be referenced in CSS and other styling
color_vars = """
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

[data-theme="dark"] {
    --primary-color: #738DF6;
    --secondary-color: #ced4da;
    --background-color: #111827;
    --surface-color: #1f2937;
    --text-color: #f8f9fa;
    --light-accent: #374151;
    --mid-accent: #4b5563;
    --dark-accent: #6b7280;
    --card-shadow: rgba(0, 0, 0, 0.25);
    --tag-bg: #374151;
    --strength-color: #34D399;
    --improve-color: #FBBF24;
    --score-high: #34D399;
    --score-mid: #FBBF24;
    --score-low: #F87171;
}
"""

custom_css = f"""
{color_vars}

.stApp {{
    background-color: var(--background-color);
    color: var(--text-color);
}}

.stTabs [data-baseweb="tab-list"] {{
    gap: 2px;
}}

.stTabs [data-baseweb="tab"] {{
    background-color: var(--surface-color);
    color: var(--text-color);
    border-radius: 4px 4px 0 0;
}}

.stTabs [aria-selected="true"] {{
    background-color: var(--primary-color) !important;
    color: white !important;
}}

div.card {{
    border-radius: 10px;
    background-color: var(--surface-color);
    padding: 1.5rem;
    margin-bottom: 1rem;
    box-shadow: 0 4px 6px var(--card-shadow);
}}

div.keyword-tag {{
    display: inline-block;
    background-color: var(--tag-bg);
    border-radius: 20px;
    padding: 8px 16px;
    margin: 5px;
    font-weight: 500;
    text-align: center;
}}

div.trend-card {{
    background-color: var(--surface-color);
    padding: 15px;
    margin: 10px 0;
    border-left: 4px solid var(--primary-color);
    border-radius: 5px;
}}

.match-score-high {{
    color: var(--score-high);
    font-size: 3.5rem;
    font-weight: bold;
}}

.match-score-mid {{
    color: var(--score-mid);
    font-size: 3.5rem;
    font-weight: bold;
}}

.match-score-low {{
    color: var(--score-low);
    font-size: 3.5rem;
    font-weight: bold;
}}

.strength-item {{
    color: var(--strength-color);
    margin-bottom: 0.5rem;
}}

.improvement-item {{
    color: var(--improve-color);
    margin-bottom: 0.5rem;
}}

/* Theme toggle button styling */
.theme-toggle {{
    position: fixed;
    top: 10px;
    right: 10px;
    z-index: 1000;
}}

/* Enhancing form inputs */
div[data-baseweb="input"] input, 
div[data-baseweb="textarea"] textarea {{
    background-color: var(--surface-color);
    color: var(--text-color);
    border: 1px solid var(--mid-accent);
}}

/* Button styling */
.stButton button {{
    border-radius: 6px;
}}

.stButton > button[data-baseweb="button"] {{
    border: 1px solid var(--mid-accent);
}}
"""

st.markdown(f"""
<style>{custom_css}</style>
""", unsafe_allow_html=True)

# === ERROR TRACKING SYSTEM ===
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

# === AUTHENTICATION SYSTEM ===
def check_password():
    """Returns `True` if the user had a correct password."""

    def login_form():
        """Form with widgets to collect user information"""
        with st.form("Credentials"):
            st.text_input("Username", key="username")
            st.text_input("Password", type="password", key="password")
            st.form_submit_button("Log in", on_click=password_entered)

    def password_entered():
        """Checks whether a password entered by the user is correct."""
        # Ensure secrets and passwords structure exists before accessing
        if "passwords" in st.secrets and st.session_state["username"] in st.secrets["passwords"]:
            stored_password = st.secrets.passwords[st.session_state["username"]]
            # Ensure stored_password is a string or bytes for hmac.compare_digest
            if isinstance(stored_password, (str, bytes)):
                 if hmac.compare_digest(
                    st.session_state["password"],
                    str(stored_password) # Ensure it's compared as string if needed
                 ):
                    st.session_state["password_correct"] = True
                    del st.session_state["password"]  # Don't store the username or password.
                    del st.session_state["username"]
                    return # Exit function on success
            else:
                 st.error(f"Password configuration error for user {st.session_state['username']}.")

        # If checks failed or structure doesn't exist
        st.session_state["password_correct"] = False


    # Return True if the username + password is validated.
    if st.session_state.get("password_correct", False):
        return True

    # Show inputs for username + password.
    login_form()
    if "password_correct" in st.session_state and not st.session_state["password_correct"]:
        st.error("😕 User not known or password incorrect")
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
    st.markdown("*These keywords appear in the job description but are missing or underemphasised in your resume:*")
    
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

def display_resume_summary(resume_data):
    """Display a summary of the parsed resume."""
    if resume_data:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        # Name and contact
        st.markdown(f"### {resume_data.get('name', 'Candidate')}")
        contact = resume_data.get('contact_info', {})
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
        skills = resume_data.get('skills', {})
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
        experience = resume_data.get('work_experience', [])
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
        education = resume_data.get('education', [])
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
        certifications = resume_data.get('certifications', [])
        if certifications:
            st.markdown("#### Certifications")
            for cert in certifications:
                st.markdown(f"- {cert}")
        
        st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.markdown("*No resume data available*")

# === THEME TOGGLE FUNCTIONALITY ===
def toggle_theme():
    """Toggle between light and dark themes"""
    current_theme = st.session_state.get("theme", "light")
    if current_theme == "light":
        st.session_state["theme"] = "dark"
    else:
        st.session_state["theme"] = "light"

# Initialize theme in session state if not present
if "theme" not in st.session_state:
    # Default to system preference or light
    st.session_state["theme"] = "light"

# Apply the current theme using HTML
current_theme = st.session_state.get("theme", "light")
st.markdown(f"""
<script>
    document.body.setAttribute('data-theme', '{current_theme}');
</script>
""", unsafe_allow_html=True)

# === ANALYSIS FUNCTIONS ===
@lru_cache(maxsize=10)  # Cache for performance
def parse_resume(client, resume_text, candidate_name):
    """
    Parses a resume and returns a dictionary with structured data.
    Uses caching for performance improvements.
    """
    if not resume_text or len(resume_text.strip()) < 50:
        error_tracker.add_error("parse_error", "Your resume contains too little text to parse effectively.", False)
        # Return fallback structure
        return {
            "name": candidate_name,
            "contact_info": {"email": None, "phone": None},
            "education": [],
            "work_experience": [{"title": "Unknown", "description": "Resume text extraction failed or contained too little text."}],
            "skills": {"technical": [], "soft": []},
            "certifications": [],
            "original_filename": candidate_name,
            "parsing_error": "Text extraction failed or insufficient content"
        }

    prompt = f"""
    Please extract the following information from the resume provided below for candidate '{candidate_name}'.
    Structure the output as a single JSON object containing these keys:
    - "name": (string, if found, otherwise use '{candidate_name}')
    - "contact_info": (object with "email" and "phone" keys, strings, null if not found)
    - "education": (array of strings or objects describing education, empty array if none)
    - "work_experience": (array of strings or objects describing work experience including years/duration, empty array if none)
    - "skills": (object with "technical" and "soft" keys, each containing an array of strings, empty arrays if none)
    - "certifications": (array of strings, empty array if none)
    - "original_filename": (string, always include '{candidate_name}')

    IMPORTANT: Respond ONLY with the valid JSON object. Do not include any introductory text, explanations, or markdown formatting like ```json.

    Resume for candidate {candidate_name}:
    ---
    {resume_text}
    ---
    """

    # Use enhanced API call with timeout
    success, response_text = call_anthropic_api_with_timeout(
        client=client,
        prompt=prompt,
        max_tokens=1500,
        temperature=0.0,
        system="You are an expert resume parser. Extract structured information accurately and return ONLY a valid JSON object as specified.",
        timeout=45,  # 45 second timeout
        retries=1    # 1 retry attempt
    )

    if not success:
        error_tracker.add_error("api_error", f"API call failed during resume parsing: {response_text}", True)
        # Return fallback structure on API failure
        return {
            "name": candidate_name,
            "contact_info": {"email": None, "phone": None},
            "education": [],
            "work_experience": [{"title": "Unknown", "description": "API call failed during resume parsing."}],
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

def analyze_resume_match(client, resume_data, job_description):
    """
    Analyses how well a resume matches with a job description.
    Returns a match analysis with scores and recommendations.
    """
    if not resume_data:
        error_tracker.add_error("parse_error", "No resume data provided for analysis.", True)
        return None
        
    if not job_description or len(job_description.strip()) < 50:
        error_tracker.add_error("parse_error", "Job description is too short for meaningful analysis.", False)
        job_description += "\n\nThis is a professional position requiring technical skills and relevant experience."

    # Convert resume data to a JSON string for the prompt
    try:
        resume_json_string = json.dumps(resume_data, indent=2)
    except Exception as e:
        error_tracker.add_error("json_error", "Error converting resume data to JSON", True, str(e))
        return None

    prompt = f"""
    You are an expert job application consultant. Based on the job description below and the provided resume data, 
    analyse how well the candidate matches the job requirements and provide constructive feedback.

    Job Description:
    ---
    {job_description}
    ---

    Resume Data (JSON):
    ---
    {resume_json_string}
    ---

    Perform a thorough analysis of the match between this candidate and the job description, including:
    1. An overall "match_score" from 0 to 100, representing their fit for the position.
    2. Three to five key "strengths" that make them a good fit for this specific role.
    3. Three to five main "improvement_areas" where they could enhance their candidacy.
    4. A "skills_assessment" object with ratings (0-100) for these specific categories:
       - "Technical Skills" (relevance to the role)
       - "Experience" (years and quality related to the role)
       - "Education" (relevance and level)
       - "Resume Quality" (clarity, formatting, and presentation)
    5. "recommendations" - practical, specific suggestions to improve their resume and application for this role.
    6. "keyword_analysis" - identify key terms from the job description missing from their resume.
    7. "industry_fit" - assessment of how well the candidate matches the industry requirements for this role.
    8. "potential_job_titles" - alternate job titles that this resume would be well-suited for.
    9. "experience_gap_analysis" - identify specific experience gaps between the resume and job requirements.

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
        error_tracker.add_error("api_error", f"API call failed during resume analysis: {response_text}", True)
        # Return a basic fallback analysis
        return {
            "match_score": 50, 
            "strengths": ["Unable to analyze due to API error"],
            "improvement_areas": ["Unable to analyze due to API error"],
            "skills_assessment": {
                "Technical Skills": 50,
                "Experience": 50,
                "Education": 50,
                "Resume Quality": 50
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
            "Resume Quality": 50
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
                        "Resume Quality": 50
                    }
                elif field == "match_score":
                    analysis_data[field] = 50
                elif field == "industry_fit":
                    analysis_data[field] = "Unknown"
        
        return analysis_data
        
    except json.JSONDecodeError as json_e:
        error_tracker.add_error("json_error", f"Failed to decode analysis JSON: {json_e}", True)
        return fallback_analysis

def generate_interview_tips(client, resume_data, job_description, analysis):
    """
    Generates personalised interview tips based on resume and job description.
    """
    if not resume_data or not job_description or not analysis:
        return ["Unable to generate interview tips due to missing data."]
    
    # Extract key areas where improvement might be needed
    improvement_areas = analysis.get('improvement_areas', [])
    strengths = analysis.get('strengths', [])
    match_score = analysis.get('match_score', 50)
    
    # Convert data to JSON for the prompt
    try:
        resume_json = json.dumps(resume_data, indent=2)
        analysis_json = json.dumps(analysis, indent=2)
    except Exception as e:
        error_tracker.add_error("json_error", f"Error preparing data for interview tips: {e}", False)
        return ["Error generating interview tips."]
    
    prompt = f"""
    You are an expert career coach. Based on this candidate's resume and job description analysis, 
    provide 5 strategic interview preparation tips tailored specifically to them.

    Job Description:
    ---
    {job_description}
    ---

    Resume Data:
    ---
    {resume_json}
    ---
    
    Resume Analysis:
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

def analyze_industry_fit(client, resume_data, job_description, analysis):
    """
    Analyzes how well the candidate fits within the specific industry context.
    """
    if not resume_data or not job_description or not analysis:
        return None
    
    # Convert data to JSON for the prompt
    try:
        resume_json = json.dumps(resume_data, indent=2)
        analysis_json = json.dumps(analysis, indent=2)
    except Exception as e:
        error_tracker.add_error("json_error", f"Error preparing data for industry analysis: {e}", False)
        return None
    
    prompt = f"""
    You are an expert industry analyst specializing in career placement. Based on this candidate's resume, 
    the job description, and previous analysis, provide an industry-specific assessment.

    Job Description:
    ---
    {job_description}
    ---

    Resume Data:
    ---
    {resume_json}
    ---
    
    Resume Analysis:
    ---
    {analysis_json}
    ---

    Provide a JSON response with the following structure:
    1. "industry_identified": the specific industry this job is in
    2. "industry_fit_score": numeric score from 0-100 on industry fit
    3. "industry_trends": array of current trends in this industry relevant to the role
    4. "industry_keywords": array of industry-specific keywords that would strengthen the resume
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

def generate_comprehensive_report(resume_data, job_description, analysis, industry_analysis):
    """
    Generates a detailed PDF-ready report with all analyses.
    """
    # For now, we'll generate a structured markdown report that can be saved
    report_parts = []
    
    # Title and header
    report_parts.append(f"# Resume Analysis Report\n")
    report_parts.append(f"**Candidate:** {resume_data.get('name', 'Candidate')}\n")
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
        report_parts.append("Keywords that appear in the job description but are missing or underemphasised in your resume:\n")
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
    report_parts.append("1. Update your resume based on the recommendations above\n")
    report_parts.append("2. Prepare for interviews using the interview tips provided separately\n")
    report_parts.append("3. Research the industry trends and competitors identified\n")
    report_parts.append("4. Consider applying for the alternate job titles suggested if appropriate\n")
    
    # Join all parts
    return "".join(report_parts)

def generate_cover_letter(client, resume_data, job_description, analysis):
    """
    Generates a customised cover letter based on resume, job description, and match analysis.
    """
    if not resume_data or not job_description or not analysis:
        return "Unable to generate cover letter due to missing data."
    
    # Extract key information to personalise the cover letter
    candidate_name = resume_data.get('name', 'Candidate')
    strengths = analysis.get('strengths', [])
    keywords = analysis.get('keyword_analysis', [])
    skills_assessment = analysis.get('skills_assessment', {})
    
    # Convert data to JSON for the prompt
    try:
        resume_json = json.dumps(resume_data, indent=2)
        analysis_json = json.dumps(analysis, indent=2)
    except Exception as e:
        error_tracker.add_error("json_error", "Error preparing data for cover letter", False, str(e))
        return "Error generating cover letter."
    
    prompt = f"""
    You are an expert career consultant. Based on this candidate's resume and the job description analysis, 
    create a professional cover letter that highlights their relevant qualifications and fit for the role.

    Job Description:
    ---
    {job_description}
    ---

    Resume Data:
    ---
    {resume_json}
    ---
    
    Resume Analysis:
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

def store_analysis_history(resume_data, job_description, analysis):
    """
    Stores analysis history in session state for trend tracking.
    """
    # Initialize history if it doesn't exist
    if 'analysis_history' not in st.session_state:
        st.session_state['analysis_history'] = []
        
    # Create a record of this analysis
    timestamp = datetime.now().isoformat()
    resume_name = resume_data.get('name', 'Unknown')
    match_score = analysis.get('match_score', 0)
    
    # Extract job title from description (simple approach)
    job_title = "Unknown Position"
    first_line = job_description.strip().split('\n')[0]
    if len(first_line) < 100:  # Likely a title
        job_title = first_line
        
    # Create history entry
    entry = {
        "timestamp": timestamp,
        "resume_name": resume_name,
        "job_title": job_title,
        "match_score": match_score,
        "skills_assessment": analysis.get('skills_assessment', {}),
        "analysis_id": len(st.session_state['analysis_history'])
    }
    
    # Add to history
    st.session_state['analysis_history'].append(entry)
    
    # Keep only the last 10 entries
    if len(st.session_state['analysis_history']) > 10:
        st.session_state['analysis_history'] = st.session_state['analysis_history'][-10:]
        
    return True

def generate_trend_charts():
    """
    Generates charts showing trends across analyses.
    """
    if 'analysis_history' not in st.session_state or len(st.session_state['analysis_history']) < 2:
        return None
        
    history = st.session_state['analysis_history']
    
    # Create dataframe for analysis
    df = pd.DataFrame(history)
    
    # Extract skill assessment data for easier charting
    # This flattens the nested dictionary into columns
    skill_columns = []
    for idx, entry in enumerate(history):
        skills = entry.get('skills_assessment', {})
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

# === MAIN APPLICATION ===
def main():
    # Add theme toggle button in sidebar
    with st.sidebar:
        st.title("Settings")
        if st.button("Toggle Light/Dark Mode"):
            toggle_theme()
            st.rerun()
        
        # Information about the app
        st.markdown("---")
        st.markdown("### About CareerVertex")
        st.markdown("""
        CareerVertex analyzes your resume against job descriptions to:
        
        - Score your match with the position
        - Identify strengths and improvement areas
        - Suggest industry-specific keywords
        - Generate custom cover letters
        - Provide interview preparation tips
        
        Data is only stored in your current browser session and is automatically erased when you close this tab.
        """)
    
    # App title and introduction
    st.title("CareerVertex - Resume Job Match Analyser")
    st.markdown("*Analyse how well your resume matches a specific job description*")

    # Authentication check
    if not check_password():
        st.stop()

    # Initialize Anthropic client
    client = initialize_anthropic_client()
    if not client:
        st.stop()

    # Initialize session state more robustly
    for key in ['job_description', 'resume_file_name', 'resume_text', 'resume_data', 
               'analysis_results', 'interview_tips', 'processing_started', 'processing_completed',
               'industry_analysis', 'comprehensive_report']:
        if key not in st.session_state:
            st.session_state[key] = None
            
    # For job description, initialize as empty string
    if st.session_state['job_description'] is None:
        st.session_state['job_description'] = ""
        
    # For flags, initialize as False
    for flag in ['processing_started', 'processing_completed']:
        if st.session_state[flag] is None:
            st.session_state[flag] = False

    # Define callback functions to handle state management
    def handle_job_file_upload():
        """Callback function for when a job description file is uploaded"""
        jd_file = st.session_state.get("jd_uploader")
        if jd_file:
            with st.spinner("Extracting job description text..."):
                jd_text = extract_text_from_file(jd_file)
                if jd_text:
                    st.session_state['job_description'] = jd_text

    def handle_resume_file_upload():
        """Callback function for when a resume file is uploaded"""
        # Clear previous results when a new resume is uploaded
        st.session_state['resume_file_name'] = None
        st.session_state['resume_text'] = None
        st.session_state['resume_data'] = None
        st.session_state['analysis_results'] = None
        st.session_state['interview_tips'] = None
        st.session_state['industry_analysis'] = None
        st.session_state['comprehensive_report'] = None
        st.session_state['processing_started'] = False
        st.session_state['processing_completed'] = False
                    
    def start_processing():
        """Callback function for when the analyse button is clicked"""
        # Set flag to indicate processing has started
        st.session_state['processing_started'] = True

    # Create two columns for input
    col1, col2 = st.columns(2, gap="medium")

    with col1:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.subheader("Job Description")
        # Text area for job description
        job_description = st.text_area(
            "Paste the job description here",
            value=st.session_state['job_description'],
            height=300,
            placeholder="Copy and paste the job description you're applying for..."
        )
        st.session_state['job_description'] = job_description
        
        # File uploader for job description
        st.file_uploader(
            "Or upload a job description file", 
            type=["pdf", "docx", "txt"], 
            key="jd_uploader",
            on_change=handle_job_file_upload
        )
        st.markdown('</div>', unsafe_allow_html=True)

    with col2:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.subheader("Your Resume")
        # File uploader for resume
        resume_file = st.file_uploader(
            "Upload your resume (PDF, DOCX, or TXT)",
            type=["pdf", "docx", "txt"],
            key="resume_uploader",
            on_change=handle_resume_file_upload
        )
        
        if resume_file:
            st.success(f"Resume uploaded: {resume_file.name}")
            
            # Preview button to show extracted text
            if st.button("Preview Extracted Text"):
                with st.spinner("Extracting text from resume..."):
                    resume_text = extract_text_from_file(resume_file)
                    if resume_text:
                        with st.expander("Extracted Resume Text"):
                            st.text(resume_text)
                    else:
                        st.error("Failed to extract text from your resume.")
        st.markdown('</div>', unsafe_allow_html=True)

    # Analysis button - using on_click to better control execution flow
    analyze_col1, analyze_col2, analyze_col3 = st.columns([1, 2, 1])
    with analyze_col2:
        st.button(
            "Analyse Resume Match", 
            type="primary",
            disabled=not (job_description and resume_file) or st.session_state['processing_started'],
            on_click=start_processing,
            use_container_width=True
        )

    # Main processing logic - separated from button click
    if st.session_state['processing_started'] and not st.session_state['processing_completed']:
        if resume_file and job_description:
            # Create containers for progress tracking
            progress_container = st.container()
            
            with progress_container:
                progress_bar = st.progress(0.0)
                status_text = st.empty()
                
                # Only process if we haven't already stored data for this resume
                current_resume_name = resume_file.name
                if current_resume_name != st.session_state['resume_file_name']:
                    # Step 1: Extract text from resume
                    status_text.text("Extracting text from your resume...")
                    resume_text = extract_text_from_file(resume_file)
                    progress_bar.progress(0.15)
                    
                    if resume_text:
                        # Store resume text
                        st.session_state['resume_text'] = resume_text
                        st.session_state['resume_file_name'] = current_resume_name
                        
                        # Step 2: Parse resume
                        status_text.text("Parsing resume information...")
                        resume_data = parse_resume(client, resume_text, current_resume_name)
                        progress_bar.progress(0.30)
                        
                        if resume_data and 'parsing_error' not in resume_data:
                            # Step 3: Analyse match - main analysis
                            status_text.text("Analysing match with job description...")
                            analysis_results = analyze_resume_match(client, resume_data, job_description)
                            progress_bar.progress(0.50)
                            
                            # Step 4: Industry analysis - new feature
                            status_text.text("Conducting industry-specific analysis...")
                            industry_analysis = analyze_industry_fit(client, resume_data, job_description, analysis_results)
                            progress_bar.progress(0.65)
                            
                            # Step 5: Generate interview tips
                            status_text.text("Generating interview preparation tips...")
                            interview_tips = generate_interview_tips(client, resume_data, job_description, analysis_results)
                            progress_bar.progress(0.80)
                            
                            # Step 6: Generate comprehensive report
                            status_text.text("Creating comprehensive analysis report...")
                            comprehensive_report = generate_comprehensive_report(resume_data, job_description, analysis_results, industry_analysis)
                            progress_bar.progress(0.95)
                            
                            # Store analysis history for trend analysis
                            store_analysis_history(resume_data, job_description, analysis_results)
                            
                            # Store results in session state
                            st.session_state['resume_data'] = resume_data
                            st.session_state['analysis_results'] = analysis_results
                            st.session_state['interview_tips'] = interview_tips
                            st.session_state['industry_analysis'] = industry_analysis
                            st.session_state['comprehensive_report'] = comprehensive_report
                            
                            progress_bar.progress(1.0)
                            status_text.success("Analysis complete! View your results below.")
                        else:
                            status_text.error("Error parsing your resume. Please try a different file or format.")
                    else:
                        status_text.error("Could not extract text from your resume. Please try a different file.")
                else:
                    # We've already processed this resume, just show the message
                    status_text.success("Resume already analysed. View your results below.")
                    progress_bar.progress(1.0)
                    
                # Mark processing as completed so it won't run again
                st.session_state['processing_completed'] = True
                
        # Display any errors that were tracked
        error_tracker.display_errors()

    # Display results if available
    if st.session_state['analysis_results'] is not None:
        analysis_results = st.session_state['analysis_results']
        resume_data = st.session_state['resume_data']
        industry_analysis = st.session_state.get('industry_analysis')
        
        st.markdown("---")
        
        # Create tabs for different views of the analysis
        overview_tab, details_tab, industry_tab, trends_tab, report_tab = st.tabs([
            "Overview", "Detailed Analysis", "Industry Insights", "Trend Analysis", "Full Report"
        ])
        
        # OVERVIEW TAB
        with overview_tab:
            # Main score section
            st.header("Resume Match Analysis")
            st.markdown('<div class="card">', unsafe_allow_html=True)
            score_col1, score_col2 = st.columns([1, 3])
            
            with score_col1:
                match_score = analysis_results.get('match_score', 0)
                display_match_score(match_score)
                
                # Add a reset button to allow analysing another resume
                if st.button("Reset & Analyse Another Resume"):
                    # Clear the processing flags and results
                    st.session_state['resume_file_name'] = None
                    st.session_state['resume_text'] = None
                    st.session_state['resume_data'] = None
                    st.session_state['analysis_results'] = None
                    st.session_state['interview_tips'] = None
                    st.session_state['industry_analysis'] = None
                    st.session_state['comprehensive_report'] = None
                    st.session_state['processing_started'] = False
                    st.session_state['processing_completed'] = False
                    st.rerun()
                
            with score_col2:
                # Skill assessment visualization - improved visualization
                st.subheader("Skills Assessment")
                skills_assessment = analysis_results.get('skills_assessment', {})
                
                skills_chart = create_skills_chart(skills_assessment)
                if skills_chart:
                    st.altair_chart(skills_chart, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)
            
            # Strengths and improvement areas
            display_strengths_and_improvements(strengths=analysis_results.get('strengths', []), 
                                              improvements=analysis_results.get('improvement_areas', []))
            
            # Quick action buttons
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.subheader("Quick Actions")
            qa_col1, qa_col2, qa_col3 = st.columns(3)
            
            with qa_col1:
                if st.button("Generate Cover Letter", use_container_width=True):
                    with st.spinner("Creating your customised cover letter..."):
                        cover_letter = generate_cover_letter(client, resume_data, job_description, analysis_results)
                        st.session_state['cover_letter'] = cover_letter
                        st.success("Cover letter created! Check the Full Report tab.")
            
            with qa_col2:
                if st.button("View Interview Tips", use_container_width=True):
                    st.session_state['show_interview_tips'] = True
                    st.success("Interview tips ready! Check the Detailed Analysis tab.")
            
            with qa_col3:
                if st.button("Download Full Report", use_container_width=True):
                    if st.session_state.get('comprehensive_report'):
                        report_text = st.session_state['comprehensive_report']
                        st.download_button(
                            label="Download Report as Markdown",
                            data=report_text,
                            file_name="resume_analysis_report.md",
                            mime="text/markdown",
                            use_container_width=True
                        )
            st.markdown('</div>', unsafe_allow_html=True)
        
        # DETAILS TAB
        with details_tab:
            st.header("Detailed Analysis")
            
            # Display interview tips if requested
            if st.session_state.get('show_interview_tips', False):
                st.markdown('<div class="card">', unsafe_allow_html=True)
                st.subheader("Interview Preparation Tips")
                interview_tips = st.session_state.get('interview_tips')
                if interview_tips and isinstance(interview_tips, str):
                    st.markdown(interview_tips)
                elif interview_tips and isinstance(interview_tips, list):
                    for tip in interview_tips:
                        st.markdown(tip)
                else:
                    st.markdown("*Unable to generate interview tips.*")
                st.markdown('</div>', unsafe_allow_html=True)
            
            # Recommendations section
            display_recommendations(analysis_results.get('recommendations', []))
            
            # Keyword Analysis - improved display
            st.markdown('<div class="card">', unsafe_allow_html=True)
            keywords = analysis_results.get('keyword_analysis', [])
            display_keywords(keywords, max_cols=3)
            st.markdown('</div>', unsafe_allow_html=True)
            
            # Experience Gap Analysis - new section
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.subheader("Experience Gap Analysis")
            experience_gaps = analysis_results.get('experience_gap_analysis', [])
            if experience_gaps:
                for gap in experience_gaps:
                    st.markdown(f"🔸 **{gap}**")
            else:
                st.markdown("*No specific experience gaps identified.*")
            st.markdown('</div>', unsafe_allow_html=True)
                
            # Potential Alternative Job Titles - new section
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.subheader("Alternative Job Titles to Consider")
            alt_titles = analysis_results.get('potential_job_titles', [])
            if alt_titles:
                st.markdown("Based on your resume, you might also be a good fit for these roles:")
                for title in alt_titles:
                    st.markdown(f"🔹 **{title}**")
            else:
                st.markdown("*No alternative job titles suggested.*")
            st.markdown('</div>', unsafe_allow_html=True)
        
        # INDUSTRY TAB
        with industry_tab:
            st.header("Industry Insights")
            
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
                        
                    st.markdown(f"**Industry Fit Score:** :{ind_color}[{industry_fit}%] - {ind_text}")
                    
                    # Salary information
                    salary_range = industry_analysis.get('salary_range', {})
                    if salary_range and salary_range.get('min', 0) > 0:
                        st.markdown(f"**Typical Salary Range:** £{salary_range.get('min', 0):,} - £{salary_range.get('max', 0):,}")
                
                with industry_col2:
                    # Top competitors
                    st.subheader("Key Companies in This Space")
                    competitors = industry_analysis.get('competitors', [])
                    if competitors:
                        for company in competitors:
                            st.markdown(f"🏢 **{company}**")
                    else:
                        st.markdown("*No competitor information available.*")
                st.markdown('</div>', unsafe_allow_html=True)
                
                # Current trends section with improved styling
                st.markdown('<div class="card">', unsafe_allow_html=True)
                st.subheader("Current Industry Trends")
                trends = industry_analysis.get('industry_trends', [])
                display_trends(trends, max_cols=2)
                st.markdown('</div>', unsafe_allow_html=True)
                
                # Industry challenges section
                st.markdown('<div class="card">', unsafe_allow_html=True)
                st.subheader("Current Industry Challenges")
                challenges = industry_analysis.get('industry_challenges', [])
                if challenges:
                    for challenge in challenges:
                        st.markdown(f"⚠️ **{challenge}**")
                else:
                    st.markdown("*No industry challenges identified.*")
                st.markdown('</div>', unsafe_allow_html=True)
                
                # Industry keywords
                st.markdown('<div class="card">', unsafe_allow_html=True)
                st.subheader("Industry-Specific Keywords")
                st.markdown("*Adding these industry-specific keywords to your resume could improve your chances:*")
                
                ind_keywords = industry_analysis.get('industry_keywords', [])
                display_keywords(ind_keywords, max_cols=3)
                st.markdown('</div>', unsafe_allow_html=True)
            else:
                st.info("Industry analysis is not available. Please try running the analysis again.")
        
        # TRENDS TAB
        with trends_tab:
            st.header("Trend Analysis")
            
            if 'analysis_history' in st.session_state and len(st.session_state['analysis_history']) > 1:
                st.success(f"We've analyzed {len(st.session_state['analysis_history'])} different job applications. Here's how you're doing!")
                
                # Show performance over time
                charts = generate_trend_charts()
                if charts:
                    st.markdown('<div class="card">', unsafe_allow_html=True)
                    # Match score trend
                    st.subheader("Application Match Score Trend")
                    st.altair_chart(charts.get('match_score'), use_container_width=True)
                    st.markdown('</div>', unsafe_allow_html=True)
                    
                    # Skills comparison across jobs
                    if 'skills' in charts:
                        st.markdown('<div class="card">', unsafe_allow_html=True)
                        st.subheader("Skills Assessment Across Applications")
                        st.altair_chart(charts.get('skills'), use_container_width=True)
                        st.markdown('</div>', unsafe_allow_html=True)
                    
                    # Analysis and insights
                    st.markdown('<div class="card">', unsafe_allow_html=True)
                    st.subheader("Trend Insights")
                    
                    # Create a dataframe from the history
                    history = st.session_state['analysis_history']
                    df = pd.DataFrame(history)
                    
                    # Calculate average match score
                    avg_score = df['match_score'].mean()
                    max_score = df['match_score'].max()
                    min_score = df['match_score'].min()
                    
                    st.markdown(f"""
                    📊 **Match Score Statistics:**
                    - **Average Match Score:** {avg_score:.1f}%
                    - **Highest Match Score:** {max_score:.1f}% 
                    - **Lowest Match Score:** {min_score:.1f}%
                    """)
                    
                    # Show jobs with highest scores
                    st.markdown("### Your Best Matches")
                    best_matches = df.sort_values('match_score', ascending=False).head(3)
                    for i, match in best_matches.iterrows():
                        st.markdown(f"""
                        **{match['job_title']}** - {match['match_score']}% match  
                        *Analyzed on {pd.to_datetime(match['timestamp']).strftime('%B %d, %Y')}*
                        """)
                    st.markdown('</div>', unsafe_allow_html=True)
                else:
                    st.warning("Unable to generate trend charts with the available data.")
            else:
                st.markdown('<div class="card">', unsafe_allow_html=True)
                st.info("Trend analysis requires at least two job applications. Try analyzing another job to compare.")
                st.markdown("""
                ### How Trend Analysis Works
                
                Once you've analyzed multiple job applications, this section will show:
                
                1. **Match Score Trends** - How your match score varies across different job types
                2. **Skills Comparison** - Which skills are consistently strong or weak across applications
                3. **Industry Insights** - Patterns in how well you match with different industries
                4. **Targeted Improvement Areas** - Consistent gaps to address in your resume
                
                Try analyzing a few different job descriptions to unlock these insights!
                """)
                st.markdown('</div>', unsafe_allow_html=True)
        
        # REPORT TAB
        with report_tab:
            st.header("Comprehensive Report")
            
            # Calculate and display token count for the report
            comprehensive_report = st.session_state.get('comprehensive_report')
            if comprehensive_report:
                report_tokens = len(comprehensive_report.split())
                st.info(f"Report length: {report_tokens} tokens")
            
            # Cover letter section
            st.markdown('<div class="card">', unsafe_allow_html=True)
            if 'cover_letter' in st.session_state and st.session_state['cover_letter']:
                with st.expander("Your Customised Cover Letter", expanded=True):
                    st.markdown(st.session_state['cover_letter'])
                    
                    # Add option to download cover letter as text file
                    cover_letter_text = st.session_state['cover_letter']
                    st.download_button(
                        label="Download Cover Letter",
                        data=cover_letter_text,
                        file_name="cover_letter.txt",
                        mime="text/plain"
                    )
            else:
                # Button to generate cover letter
                if st.button("Generate Custom Cover Letter"):
                    with st.spinner("Creating your customised cover letter..."):
                        cover_letter = generate_cover_letter(client, resume_data, job_description, analysis_results)
                        st.session_state['cover_letter'] = cover_letter
                        st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
            
            # Full report
            if comprehensive_report:
                st.markdown('<div class="card">', unsafe_allow_html=True)
                with st.expander("Full Analysis Report", expanded=True):
                    st.markdown(comprehensive_report)
                    
                    # Offer download
                    st.download_button(
                        label="Download Full Report as Markdown",
                        data=comprehensive_report,
                        file_name="resume_analysis_report.md",
                        mime="text/markdown"
                    )
                st.markdown('</div>', unsafe_allow_html=True)
            
            # Resume summary
            display_resume_summary(resume_data)
        
            # Data retention policy
            st.markdown('<div class="card">', unsafe_allow_html=True)
            with st.expander("Data Retention Policy"):
                st.markdown("""
                ### How We Handle Your Data
                
                - **Session-Based Storage**: Your data is only stored in your current browser session
                - **No External Database**: We don't save your resume or job descriptions to any external database
                - **No Data Sharing**: Your information is not shared with third parties
                - **Automatic Cleanup**: All data is automatically erased when you close your browser tab
                
                To manually delete all data, click the "Reset & Analyse Another Resume" button or close this tab.
                """)
            st.markdown('</div>', unsafe_allow_html=True)

    # Footer
    st.markdown("---")
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("### How to Use This Analysis")
    st.markdown("""
    1. **Review your match score** to understand your overall fit for the position
    2. **Focus on improving areas** identified in the analysis
    3. **Add missing keywords** to your resume for better ATS matching
    4. **Use industry insights** to better tailor your application to the specific field
    5. **Prepare for interviews** using the provided tips
    6. **Use the generated cover letter** to create a tailored application highlighting your strengths
    7. **Track your progress** across multiple job applications with the trend analysis
    8. **Download the full report** for your records or to discuss with a career counselor
    """)
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("Powered by Claude AI")
    st.caption("This tool uses AI to provide resume analysis and should be used as a guide only. Final decisions should always be made by human recruiters.")

if __name__ == "__main__":
    main()
