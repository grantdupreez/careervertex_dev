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

.stTabs [data-baseweb="tab-list"] {
    gap: 2px;
}

.stTabs [data-baseweb="tab"] {
    background-color: var(--surface-color);
    color: var(--text-color);
    border-radius: 4px 4px 0 0;
}

.stTabs [aria-selected="true"] {
    background-color: var(--primary-color) !important;
    color: white !important;
}

div.card {
    border-radius: 10px;
    background-color: var(--surface-color);
    padding: 1.5rem;
    margin-bottom: 1rem;
    box-shadow: 0 4px 6px var(--card-shadow);
}

div.keyword-tag {
    display: inline-block;
    background-color: var(--tag-bg);
    border-radius: 20px;
    padding: 8px 16px;
    margin: 5px;
    font-weight: 500;
    text-align: center;
}

div.trend-card {
    background-color: var(--surface-color);
    padding: 15px;
    margin: 10px 0;
    border-left: 4px solid var(--primary-color);
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
}

.improvement-item {
    color: var(--improve-color);
    margin-bottom: 0.5rem;
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
    border: 1px solid var(--mid-accent);
}

.stButton button {
    border-radius: 6px;
}

.stButton > button[data-baseweb="button"] {
    border: 1px solid var(--mid-accent);
}

.pricing-card {
    border: 1px solid var(--mid-accent);
    border-radius: 10px;
    padding: 20px;
    text-align: center;
    background-color: var(--surface-color);
    box-shadow: 0 4px 6px var(--card-shadow);
    height: 100%;
}

.pricing-card h3 {
    color: var(--primary-color);
    margin-bottom: 15px;
}

.pricing-price {
    font-size: 2rem;
    font-weight: bold;
    margin: 15px 0;
}

.pricing-period {
    font-size: 0.9rem;
    opacity: 0.8;
}

.feature-item {
    margin: 8px 0;
    text-align: left;
}

.feature-item i {
    color: var(--primary-color);
    margin-right: 5px;
}

.subscription-badge {
    display: inline-block;
    background-color: var(--primary-color);
    color: white;
    padding: 5px 10px;
    border-radius: 15px;
    font-size: 0.8rem;
    font-weight: bold;
}

.subscription-badge.expired {
    background-color: var(--score-low);
}

.user-profile {
    border-radius: 10px;
    padding: 15px;
    background-color: var(--surface-color);
    margin-bottom: 15px;
}

.user-avatar {
    width: 50px;
    height: 50px;
    border-radius: 25px;
    background-color: var(--primary-color);
    color: white;
    display: flex;
    align-items: center;
    justify-content: center;
    font-weight: bold;
    font-size: 1.2rem;
    margin-right: 15px;
}
"""

st.markdown(f"""
<style>{custom_css}</style>
""", unsafe_allow_html=True)

# === INITIALIZATION ===
@st.cache_resource
def init_resources():
    """Initialize and cache resources."""
    print("Initializing resources...")
    
    # Initialize database manager
    db_manager = DatabaseManager()
    
    # Initialize schema
    try:
        db_manager.initialize_schema()
    except Exception as e:
        print(f"Schema initialization failed: {str(e)}")
    
    # Initialize auth manager
    auth_manager = AuthManager(db_manager)
    
    # Initialize error tracker
    error_tracker = ErrorTracker()
    
    return db_manager, auth_manager, error_tracker

# Initialize resources
db_manager, auth_manager, error_tracker = init_resources()

# Store in session state for access in other modules
st.session_state['db_manager'] = db_manager
st.session_state['auth_manager'] = auth_manager
st.session_state['error_tracker'] = error_tracker

# === MAIN APPLICATION ===
def main():
    """Main application entry point."""
    st.write("Application starting...")  # Debug line
    
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