import streamlit as st
import pandas as pd
import altair as alt
import numpy as np
import json
import os
import uuid
import bcrypt
from datetime import datetime, timedelta

# Import our modules
from db_manager import DatabaseManager, save_cv, get_user_cvs, get_cv_by_id, save_job_description
from db_manager import save_analysis_result, get_user_analyses, get_analysis_by_id, update_cv_parsed_data
from auth_manager import AuthManager
from utils import ErrorTracker, extract_text_from_file
from ai_analysis import initialize_anthropic_client, parse_cv, analyze_cv_match
from ai_analysis import generate_interview_tips, generate_cover_letter
from payment_manager import create_stripe_checkout_session, handle_successful_payment
from ui_components import display_match_score, display_strengths_and_improvements
from ui_components import display_recommendations, display_keywords, display_cv_summary
from ui_components import display_user_profile, display_pricing, create_skills_chart
from pages import show_login_page, show_admin_page, show_dashboard

# === APP CONFIGURATION ===
st.set_page_config(
    page_title="CareerVertex - CV Job Match Analyser",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# === CUSTOM CSS ===
custom_css = """
:root {
    --primary: #0A1F3D; /* Deep Navy Blue */
    --secondary: #B8860B; /* Dark Goldenrod */
    --secondary-light: #D4AF37; /* Pale Goldenrod (lighter gold) */
    --light: #F8F9FA; /* Very Light Gray */
    --dark: #0D1117; /* Rich Black */
    --accent: #1E5A94; /* Steel Blue */
    --gray-light: #F0F2F5; /* Lightest Gray */
    --gray: #E1E5EA; /* Light Gray */
    --success: #10B981; /* Emerald Green */
    --error: #EF4444; /* Red */
    
    /* Legacy color mappings for compatibility */
    --primary-color: var(--primary);
    --secondary-color: var(--secondary);
    --background-color: var(--light);
    --surface-color: #ffffff;
    --text-color: var(--dark);
    --light-accent: var(--gray);
    --mid-accent: var(--gray);
    --dark-accent: #adb5bd;
    --card-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    --tag-bg: var(--gray-light);
    --strength-color: var(--success);
    --improve-color: var(--secondary);
    --score-high: var(--success);
    --score-mid: var(--secondary);
    --score-low: var(--error);
    --error-bg: #f8d7da;
    --error-border: #f5c6cb;
    --error-text: #721c24;
    --warning-bg: #fff3cd;
    --warning-border: #ffeaa7;
    --warning-text: #856404;
}

.stApp {
    background-color: var(--background-color);
    color: var(--text-color);
}

/* Style primary buttons to match the gold gradient */
.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, var(--secondary) 0%, var(--secondary-light) 100%);
    color: var(--dark);
    border: none;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    box-shadow: 0 5px 15px rgba(184, 134, 11, 0.2);
    transition: all 0.4s ease;
}

.stButton > button[kind="primary"]:hover {
    transform: translateY(-3px);
    box-shadow: 0 10px 20px rgba(184, 134, 11, 0.3);
}

/* Style regular buttons */
.stButton > button {
    border-radius: 2px;
    border: 1px solid var(--gray);
    transition: all 0.3s ease;
}

.stButton > button:hover {
    border-color: var(--secondary);
    color: var(--secondary);
}

/* Style headers with the Playfair Display feel */
h1, h2, h3, h4, h5 {
    color: var(--primary);
    font-weight: 600;
}

/* Gold gradient text */
.gold-gradient {
    background: linear-gradient(135deg, var(--secondary) 0%, var(--secondary-light) 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    display: inline;
}

.stTabs [data-baseweb="tab-list"] {
    gap: 2px;
    background-color: transparent;
}

.stTabs [data-baseweb="tab"] {
    background-color: var(--surface-color);
    color: var(--primary);
    border-radius: 4px 4px 0 0;
    font-weight: 500;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    border: 1px solid var(--gray);
    border-bottom: none;
}

.stTabs [aria-selected="true"] {
    background: linear-gradient(135deg, var(--secondary) 0%, var(--secondary-light) 100%) !important;
    color: var(--dark) !important;
    border: none;
}

div.card {
    border-radius: 5px;
    background-color: var(--surface-color);
    padding: 1.5rem;
    margin-bottom: 1rem;
    box-shadow: 0 10px 30px rgba(0,0,0,0.03);
    border: 1px solid var(--gray);
    transition: all 0.4s ease;
}

div.card:hover {
    box-shadow: 0 20px 40px rgba(0,0,0,0.08);
    transform: translateY(-5px);
}

div.keyword-tag {
    display: inline-block;
    background: linear-gradient(135deg, rgba(184,134,11,0.1) 0%, rgba(212,175,55,0.1) 100%);
    border: 1px solid var(--secondary-light);
    border-radius: 20px;
    padding: 8px 16px;
    margin: 5px;
    font-weight: 500;
    text-align: center;
    color: var(--primary);
}

div.trend-card {
    background-color: var(--surface-color);
    padding: 15px;
    margin: 10px 0;
    border-left: 4px solid var(--secondary);
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
    font-weight: 500;
}

.improvement-item {
    color: var(--improve-color);
    margin-bottom: 0.5rem;
    font-weight: 500;
}

.custom-error {
    background-color: var(--error-bg);
    border: 1px solid var(--error-border);
    color: var(--error-text);
    padding: 12px;
    border-radius: 6px;
    margin-bottom: 10px;
}

.custom-warning {
    background-color: var(--warning-bg);
    border: 1px solid var(--warning-border);
    color: var(--warning-text);
    padding: 12px;
    border-radius: 6px;
    margin-bottom: 10px;
}

div[data-baseweb="input"] input, 
div[data-baseweb="textarea"] textarea {
    background-color: var(--surface-color);
    color: var(--text-color);
    border: 1px solid var(--gray);
    border-radius: 2px;
}

div[data-baseweb="input"] input:focus, 
div[data-baseweb="textarea"] textarea:focus {
    border-color: var(--secondary);
    box-shadow: 0 0 0 2px rgba(184,134,11,0.1);
}

/* Style file uploader */
.stFileUploader {
    border: 2px dashed var(--gray);
    border-radius: 5px;
    transition: all 0.3s ease;
}

.stFileUploader:hover {
    border-color: var(--secondary);
}

/* Style expanders */
.streamlit-expanderHeader {
    background-color: var(--gray-light);
    border-radius: 5px;
    color: var(--primary);
    font-weight: 500;
}

.streamlit-expanderHeader:hover {
    background-color: var(--gray);
}

.pricing-card {
    border: 1px solid var(--gray);
    border-radius: 8px;
    padding: 30px;
    text-align: center;
    background-color: var(--surface-color);
    box-shadow: 0 15px 40px rgba(0,0,0,0.05);
    height: 100%;
    transition: all 0.4s ease;
    overflow: hidden;
    position: relative;
}

.pricing-card::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 5px;
    background: linear-gradient(135deg, var(--secondary) 0%, var(--secondary-light) 100%);
}

.pricing-card:hover {
    transform: translateY(-10px);
    box-shadow: 0 20px 50px rgba(0,0,0,0.1);
}

.pricing-card h3 {
    color: var(--primary);
    margin-bottom: 15px;
    font-size: 24px;
}

.pricing-price {
    font-size: 48px;
    font-weight: 700;
    margin: 20px 0;
    color: var(--secondary);
}

.pricing-period {
    font-size: 18px;
    opacity: 0.8;
    font-weight: 400;
    vertical-align: middle;
}

.feature-item {
    margin: 10px 0;
    text-align: left;
    padding-left: 25px;
    position: relative;
}

.feature-item i {
    color: var(--secondary);
    margin-right: 8px;
    position: absolute;
    left: 0;
    top: 2px;
}

.subscription-badge {
    display: inline-block;
    background: linear-gradient(135deg, var(--secondary) 0%, var(--secondary-light) 100%);
    color: var(--dark);
    padding: 6px 16px;
    border-radius: 2px;
    font-size: 12px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 1px;
}

.subscription-badge.expired {
    background: var(--error);
    color: white;
}

.user-profile {
    border-radius: 5px;
    padding: 20px;
    background-color: var(--surface-color);
    margin-bottom: 15px;
    border: 1px solid var(--gray);
}

.user-avatar {
    width: 50px;
    height: 50px;
    border-radius: 50%;
    background: linear-gradient(135deg, var(--secondary) 0%, var(--secondary-light) 100%);
    color: var(--dark);
    display: flex;
    align-items: center;
    justify-content: center;
    font-weight: bold;
    font-size: 1.2rem;
    margin-right: 15px;
}

/* Style success/error messages */
.stSuccess {
    background-color: rgba(16, 185, 129, 0.1);
    border: 1px solid var(--success);
    color: var(--success);
    padding: 12px;
    border-radius: 5px;
}

.stError {
    background-color: var(--error-bg);
    border: 1px solid var(--error-border);
    color: var(--error-text);
    padding: 12px;
    border-radius: 5px;
}

.stWarning {
    background-color: var(--warning-bg);
    border: 1px solid var(--warning-border);
    color: var(--warning-text);
    padding: 12px;
    border-radius: 5px;
}

/* Style metrics */
[data-testid="metric-container"] {
    background-color: var(--surface-color);
    border: 1px solid var(--gray);
    padding: 15px;
    border-radius: 5px;
    text-align: center;
}

[data-testid="metric-container"] [data-testid="stMetricLabel"] {
    color: var(--primary);
    font-weight: 500;
    text-transform: uppercase;
    font-size: 12px;
    letter-spacing: 1px;
}

[data-testid="metric-container"] [data-testid="stMetricValue"] {
    color: var(--secondary);
    font-weight: 700;
}

/* Additional styling for forms */
.stForm {
    background-color: var(--gray-light);
    padding: 20px;
    border-radius: 5px;
    border: 1px solid var(--gray);
}

/* Style progress bars */
.stProgress > div > div > div > div {
    background: linear-gradient(135deg, var(--secondary) 0%, var(--secondary-light) 100%);
}

/* Style checkbox */
.stCheckbox > label > div[data-testid="stWidgetLabel"] {
    color: var(--primary);
}
"""

st.markdown(f"""
<style>{custom_css}</style>
""", unsafe_allow_html=True)

# === INITIALIZATION ===
def init_resources():
    """Initialize and cache resources."""
    # Only print if not already initialized
    if 'db_manager' not in st.session_state:
        print("Initializing resources...")
    
    # Initialize database manager
    db_manager = DatabaseManager()
    
    # Initialize schema - only if not already done
    if 'schema_initialized' not in st.session_state:
        try:
            db_manager.initialize_schema()
            st.session_state['schema_initialized'] = True
        except Exception as e:
            print(f"Schema initialization failed: {str(e)}")
    
    # Initialize auth manager
    auth_manager = AuthManager(db_manager)
    
    # Initialize error tracker
    error_tracker = ErrorTracker()
    
    return db_manager, auth_manager, error_tracker

# Initialize resources (without caching to avoid connection issues)
db_manager, auth_manager, error_tracker = init_resources()

# Store in session state for access in other modules
st.session_state['db_manager'] = db_manager
st.session_state['auth_manager'] = auth_manager
st.session_state['error_tracker'] = error_tracker

# === MAIN APPLICATION ===
def main():
    """Main application entry point."""
    # Remove debug line that's slowing startup
    
    # Check for Stripe session_id in URL params for payment completion
    query_params = st.query_params
    if "success" in query_params and "session_id" in query_params:
        session_id = query_params["session_id"]
        
        # Process the successful payment
        if handle_successful_payment(session_id, db_manager):
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
        show_admin_page(db_manager, auth_manager, error_tracker)
    else:
        # Check if user is logged in
        if 'user_id' in st.session_state:
            # Show user dashboard
            show_dashboard(db_manager, auth_manager, error_tracker)
        else:
            # Show login page
            show_login_page(db_manager, auth_manager, error_tracker)

if __name__ == "__main__":
    main()
