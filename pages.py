import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import altair as alt
import json
import uuid
import bcrypt
from datetime import datetime, timedelta

from db_manager import save_cv, get_user_cvs, get_cv_by_id, save_job_description
from db_manager import save_analysis_result, get_user_analyses, get_analysis_by_id, update_cv_parsed_data
from utils import extract_text_from_file
from ai_analysis import initialize_anthropic_client, parse_cv, analyze_cv_match
from ai_analysis import generate_interview_tips, generate_cover_letter
from payment_manager import create_stripe_checkout_session
from ui_components import display_match_score, display_strengths_and_improvements
from ui_components import display_recommendations, display_keywords, display_cv_summary
from ui_components import display_user_profile, display_pricing, create_skills_chart

def handle_subscription_redirect():
    """
    Handle Stripe checkout URL redirect properly.
    This should be called at the beginning of the app to check for pending redirects.
    """
    if 'checkout_url' in st.session_state and st.session_state['checkout_url']:
        checkout_url = st.session_state['checkout_url']
        # Clear the checkout URL from session state
        del st.session_state['checkout_url']
        
        # Use JavaScript to redirect to Stripe checkout
        redirect_script = f"""
        <script>
        window.location.href = "{checkout_url}";
        </script>
        """
        components.html(redirect_script, height=0)
        st.stop()  # Stop execution to prevent the rest of the app from running

def show_login_page(db_manager, auth_manager, error_tracker):
    """Display login and registration form."""
    st.title("Welcome to CareerVertex")
    st.markdown("*AI-Powered CV and Job Description Analysis*")
    
    # Split into two columns
    login_col, register_col = st.columns(2)
    
    with login_col:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.subheader("Login")
        with st.form("login_form"):
            email = st.text_input("Email")
            password = st.text_input("Password", type="password")
            submit_login = st.form_submit_button("Login", type="primary")
            
            if submit_login:
                if not email or not password:
                    st.error("Please enter both email and password.")
                else:
                    with st.spinner("Logging in..."):
                        success, result = auth_manager.login_user(email, password)
                        if success:
                            # Store user data in session state
                            st.session_state['user_id'] = result['user_id']
                            st.session_state['user_email'] = result['email']
                            st.session_state['user_name'] = result['full_name'] if result['full_name'] else email
                            st.session_state['user_data'] = result
                            st.success("Login successful!")
                            st.rerun()
                        else:
                            st.error(result)
        st.markdown('</div>', unsafe_allow_html=True)
    
    with register_col:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.subheader("Register")
        with st.form("register_form"):
            new_email = st.text_input("Email Address")
            new_password = st.text_input("Create Password", type="password")
            confirm_password = st.text_input("Confirm Password", type="password")
            full_name = st.text_input("Full Name")
            submit_register = st.form_submit_button("Create Account", type="primary")
            
            if submit_register:
                if not new_email or not new_password or not confirm_password:
                    st.error("Please fill out all required fields.")
                elif new_password != confirm_password:
                    st.error("Passwords do not match.")
                elif len(new_password) < 6:
                    st.error("Password must be at least 6 characters long.")
                else:
                    with st.spinner("Creating your account..."):
                        success, result = auth_manager.register_user(new_email, new_password, full_name)
                        if success:
                            st.success("Registration successful! Please log in.")
                        else:
                            st.error(result)
        st.markdown('</div>', unsafe_allow_html=True)
    
    # App description
    st.markdown("---")
    st.markdown("## AI-Powered CV Analysis")
    st.markdown("""
    CareerVertex uses advanced AI to match your CV with job descriptions, helping you:
    
    - Understand how well your CV matches specific job requirements
    - Identify key strengths and areas for improvement
    - Get tailored recommendations to enhance your application
    - Generate customised cover letters
    - Prepare for interviews with personalised tips
    
    Subscribe today for only **£25 per month** to unlock all features!
    """)
    
    # Pricing and features
    st.markdown("---")
    pricing_col1, pricing_col2, pricing_col3 = st.columns([1, 2, 1])
    
    with pricing_col2:
        display_pricing()

def show_admin_page(db_manager, auth_manager, error_tracker):
    """Display admin dashboard."""
    st.title("Admin Dashboard")
    
    admin_tabs = st.tabs(["User Management", "Usage Statistics", "Billing", "System Status"])
    
    with admin_tabs[0]:
        st.subheader("User Management")
        
        # Get all users from database
        users = db_manager.execute_query("SELECT * FROM users ORDER BY created_at DESC")
        
        if users:
            # Convert to DataFrame for easier display
            users_df = pd.DataFrame([dict(user) for user in users])
            
            # Add user status column
            users_df['status'] = users_df.apply(
                lambda x: 'Active' if x['subscription_status'] == 'active' and x['subscription_end'] and x['subscription_end'] > datetime.now() 
                else 'Expired' if x['subscription_status'] == 'active' 
                else 'Inactive',
                axis=1
            )
            
            # Format dates
            for date_col in ['created_at', 'last_login', 'subscription_start', 'subscription_end']:
                if date_col in users_df.columns:
                    users_df[date_col] = pd.to_datetime(users_df[date_col], errors='coerce')
                    users_df[date_col] = users_df[date_col].dt.strftime('%Y-%m-%d %H:%M')
            
            # Display user table
            st.dataframe(
                users_df[[
                    'user_id', 'email', 'full_name', 'status', 
                    'subscription_start', 'subscription_end', 'created_at', 'last_login'
                ]]
            )
            
            # User details
            selected_user = st.selectbox(
                "Select User for Details",
                options=users_df['email'].tolist(),
                format_func=lambda x: x
            )
            
            if selected_user:
                user = users_df[users_df['email'] == selected_user].iloc[0]
                
                st.markdown(f"### User: {user['full_name'] or user['email']}")
                
                # User actions
                actions_col1, actions_col2, actions_col3 = st.columns(3)
                
                with actions_col1:
                    if st.button("Reset Password"):
                        # Generate a temporary password
                        temp_password = str(uuid.uuid4())[:8]
                        
                        # Hash the password
                        password_hash = bcrypt.hashpw(temp_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                        
                        # Update in database
                        db_manager.execute_query(
                            "UPDATE users SET password_hash = %s WHERE user_id = %s",
                            (password_hash, user['user_id']),
                            fetch=False
                        )
                        
                        st.success(f"Password reset. Temporary password: {temp_password}")
                
                with actions_col2:
                    if user['status'] != 'Active':
                        if st.button("Extend Subscription (30 days)"):
                            # Set subscription dates
                            start_date = datetime.now()
                            end_date = start_date + timedelta(days=30)
                            
                            # Update in database
                            db_manager.execute_query(
                                """
                                UPDATE users 
                                SET subscription_status = 'active',
                                    subscription_start = %s,
                                    subscription_end = %s
                                WHERE user_id = %s
                                """,
                                (start_date, end_date, user['user_id']),
                                fetch=False
                            )
                            
                            st.success(f"Subscription extended by 30 days.")
                            st.rerun()
                    else:
                        if st.button("Cancel Subscription"):
                            # Update in database
                            db_manager.execute_query(
                                "UPDATE users SET subscription_status = 'inactive' WHERE user_id = %s",
                                (user['user_id'],),
                                fetch=False
                            )
                            
                            st.success(f"Subscription canceled.")
                            st.rerun()
                
                with actions_col3:
                    if st.button("Delete User", type="primary"):
                        # Confirm deletion
                        confirm = st.checkbox("I understand this will permanently delete the user and all their data")
                        
                        if confirm:
                            # Delete related records first
                            db_manager.execute_query("DELETE FROM token_usage WHERE user_id = %s", (user['user_id'],), fetch=False)
                            db_manager.execute_query("DELETE FROM analyses WHERE user_id = %s", (user['user_id'],), fetch=False)
                            db_manager.execute_query("DELETE FROM job_descriptions WHERE user_id = %s", (user['user_id'],), fetch=False)
                            db_manager.execute_query("DELETE FROM cvs WHERE user_id = %s", (user['user_id'],), fetch=False)
                            db_manager.execute_query("DELETE FROM payments WHERE user_id = %s", (user['user_id'],), fetch=False)
                            db_manager.execute_query("DELETE FROM users WHERE user_id = %s", (user['user_id'],), fetch=False)
                            
                            st.success(f"User deleted successfully.")
                            st.rerun()
        else:
            st.info("No users found in the database.")
    
    with admin_tabs[1]:
        st.subheader("Usage Statistics")
        
        # Get token usage by day
        token_usage_by_day = db_manager.execute_query(
            """
            SELECT DATE(request_date) as date, SUM(tokens_used) as tokens, COUNT(*) as requests
            FROM token_usage
            GROUP BY DATE(request_date)
            ORDER BY date DESC
            LIMIT 30
            """
        )
        
        if token_usage_by_day:
            # Convert to DataFrame
            usage_df = pd.DataFrame([dict(row) for row in token_usage_by_day])
            
            # Create chart
            usage_chart = alt.Chart(usage_df).mark_bar().encode(
                x=alt.X('date:T', title='Date'),
                y=alt.Y('tokens:Q', title='Tokens Used'),
                tooltip=['date', 'tokens', 'requests']
            ).properties(
                title='Token Usage by Day',
                height=300
            )
            
            st.altair_chart(usage_chart, use_container_width=True)
            
            # Display table
            st.dataframe(usage_df)
        else:
            st.info("No usage data available yet.")
    
    with admin_tabs[2]:
        st.subheader("Billing Information")
        
        # Get payment information
        payments = db_manager.execute_query(
            """
            SELECT p.*, u.email, u.full_name
            FROM payments p
            JOIN users u ON p.user_id = u.user_id
            ORDER BY p.payment_date DESC
            LIMIT 100
            """
        )
        
        if payments:
            # Convert to DataFrame
            payments_df = pd.DataFrame([dict(payment) for payment in payments])
            
            # Format dates
            payments_df['payment_date'] = pd.to_datetime(payments_df['payment_date']).dt.strftime('%Y-%m-%d %H:%M')
            
            # Display table
            st.dataframe(
                payments_df[[
                    'payment_id', 'email', 'full_name', 'amount', 
                    'currency', 'payment_date', 'payment_method', 'status'
                ]]
            )
            
            # Summary stats
            total_revenue = payments_df['amount'].sum()
            st.success(f"Total revenue: £{total_revenue:,.2f} from {len(payments_df)} payments")
        else:
            st.info("No payment data available yet.")
        
    with admin_tabs[3]:
        st.subheader("System Status")
        
        # Display database connection status
        db_status = "Connected" if db_manager.connection_params else "Disconnected"
        
        # Display API key status
        api_key_status = "Configured" if "ANTHROPIC_API_KEY" in st.secrets else "Missing"
        
        # Display Stripe configuration status
        stripe_status = "Configured" if "STRIPE_SECRET_KEY" in st.secrets else "Missing"
        
        # Display status information
        status_col1, status_col2 = st.columns(2)
        
        with status_col1:
            st.markdown("### Connection Status")
            st.markdown(f"**Database:** {db_status}")
            st.markdown(f"**Anthropic API:** {api_key_status}")
            st.markdown(f"**Stripe Integration:** {stripe_status}")
        
        with status_col2:
            st.markdown("### Server Information")
            st.code(f"""
            Streamlit version: {st.__version__}
            Python version: {st.__version__}
            """)

def show_dashboard(db_manager, auth_manager, error_tracker):
    """Display user dashboard."""
    
    # Check for pending Stripe checkout redirect FIRST
    handle_subscription_redirect()
    
    # Get updated user data
    user_data = None
    if 'user_id' in st.session_state:
        user_data = auth_manager.get_user_data(st.session_state['user_id'])
        if user_data:
            st.session_state['user_data'] = user_data
    
    # Check if user has active subscription
    has_subscription = False
    if user_data:
        has_subscription = auth_manager.check_subscription(user_data['user_id'])
    
    # User profile in sidebar
    with st.sidebar:
        st.title("User Profile")
        
        # User profile
        if user_data:
            display_user_profile(user_data)
            
            # Logout button
            if st.button("Logout"):
                auth_manager.logout_user()
                st.rerun()
        
        # Manage subscription
        st.markdown("---")
        if user_data and not has_subscription:
            st.warning("Your subscription is not active.")
            if st.button("Subscribe Now", type="primary", use_container_width=True):
                try:
                    with st.spinner("Creating checkout session..."):
                        checkout_session = create_stripe_checkout_session(
                            user_data['user_id'],
                            user_data['email']
                        )
                        
                        if checkout_session and checkout_session.url:
                            # Store the URL in session state
                            st.session_state['checkout_url'] = checkout_session.url
                            # Force a rerun which will trigger the redirect
                            st.rerun()
                        else:
                            st.error("Failed to create checkout session. Please try again.")
                            st.info("If this problem persists, please contact support.")
                except Exception as e:
                    st.error(f"Failed to create checkout session: {str(e)}")
                    print(f"Stripe checkout error: {str(e)}")
        
        # Information about the app
        st.markdown("---")
        st.markdown("### About CareerVertex")
        st.markdown("""
        CareerVertex analyses your CV against job descriptions to:
        
        - Score your match with the position
        - Identify strengths and improvement areas
        - Suggest industry-specific keywords
        - Generate custom cover letters
        - Provide interview preparation tips
        
        Your CV is stored securely in our database for easy comparison with multiple job descriptions.
        """)
    
    # Main content
    st.title("CareerVertex - CV Job Match Analyser")
    st.markdown("*Analyse how well your CV matches specific job descriptions*")
    
    # Check if user has subscription - if not, show pricing and subscription page
    if not has_subscription:
        st.warning("You need an active subscription to use CareerVertex features.")
        display_pricing()
        
        # Add a subscribe button in the main area too
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.button("Subscribe Now - £25/month", type="primary", use_container_width=True, key="main_subscribe"):
                try:
                    with st.spinner("Creating checkout session..."):
                        checkout_session = create_stripe_checkout_session(
                            user_data['user_id'],
                            user_data['email']
                        )
                        
                        if checkout_session and checkout_session.url:
                            st.session_state['checkout_url'] = checkout_session.url
                            st.rerun()
                        else:
                            st.error("Failed to create checkout session. Please try again.")
                except Exception as e:
                    st.error(f"Failed to create checkout session: {str(e)}")
        return
    
    # Initialize Anthropic client
    client = initialize_anthropic_client()
    if not client:
        st.error("Unable to initialize AI client. Please try again later.")
        return
    
    # Main dashboard tabs
    dashboard_tabs = st.tabs(["Analyse New Job", "My CVs", "My Analyses", "My Account"])
    
    # ANALYSE NEW JOB TAB
    with dashboard_tabs[0]:
        st.header("Analyse CV Against Job Description")
        
        # Get user's CVs
        user_cvs = get_user_cvs(db_manager, st.session_state['user_id'])
        
        # Split into two columns
        col1, col2 = st.columns(2, gap="medium")
        
        with col1:
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.subheader("Job Description")
            # Text area for job description
            job_description = st.text_area(
                "Paste the job description here",
                height=300,
                placeholder="Copy and paste the job description you're applying for..."
            )
            
            # Job details
            job_title = st.text_input("Job Title", placeholder="Enter the position title")
            company = st.text_input("Company", placeholder="Enter the company name (optional)")
            
            # File uploader for job description
            jd_file = st.file_uploader(
                "Or upload a job description file", 
                type=["pdf", "docx", "txt"], 
                key="jd_uploader"
            )
            
            if jd_file:
                with st.spinner("Extracting job description text..."):
                    jd_text = extract_text_from_file(jd_file, error_tracker)
                    if jd_text:
                        job_description = jd_text
                        st.success(f"Extracted text from {jd_file.name}")
            st.markdown('</div>', unsafe_allow_html=True)
        
        with col2:
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.subheader("Your CV")
            
            # Check if user has any CVs
            if user_cvs:
                # Let user select from existing CVs or upload a new one
                cv_option = st.radio(
                    "Select CV source:",
                    ["Use existing CV", "Upload new CV"]
                )
                
                if cv_option == "Use existing CV":
                    # Display dropdown of existing CVs
                    selected_cv = st.selectbox(
                        "Select your CV",
                        options=[cv['cv_id'] for cv in user_cvs],
                        format_func=lambda x: next((cv['cv_name'] for cv in user_cvs if cv['cv_id'] == x), "Unknown CV")
                    )
                    
                    # Show CV details
                    if selected_cv:
                        cv_data = next((cv for cv in user_cvs if cv['cv_id'] == selected_cv), None)
                        if cv_data:
                            st.info(f"Selected CV: {cv_data['cv_name']} (uploaded {cv_data['upload_date'].strftime('%d %b %Y')})")
                            
                            # Check if CV has been parsed
                            if not cv_data.get('parsed_data'):
                                with st.spinner("Parsing CV..."):
                                    # Parse CV if not already parsed
                                    parsed_data = parse_cv(client, cv_data['cv_text'], cv_data['cv_name'], error_tracker)
                                    
                                    if parsed_data:
                                        # Update CV with parsed data
                                        update_cv_parsed_data(db_manager, cv_data['cv_id'], parsed_data)
                                        cv_data['parsed_data'] = parsed_data
                else:
                    # Upload new CV
                    cv_file = st.file_uploader(
                        "Upload your CV (PDF, DOCX, or TXT)",
                        type=["pdf", "docx", "txt"],
                        key="cv_uploader"
                    )
                    
                    cv_name = st.text_input("CV Name", placeholder="Give your CV a name")
                    
                    if cv_file and cv_name:
                        with st.spinner("Extracting text from CV..."):
                            cv_text = extract_text_from_file(cv_file, error_tracker)
                            
                            if cv_text:
                                # Save CV to database
                                success, cv_id = save_cv(db_manager, st.session_state['user_id'], cv_name, cv_text)
                                
                                if success:
                                    # Parse CV
                                    with st.spinner("Parsing CV..."):
                                        parsed_data = parse_cv(client, cv_text, cv_name, error_tracker)
                                        
                                        if parsed_data:
                                            # Update CV with parsed data
                                            update_cv_parsed_data(db_manager, cv_id, parsed_data)
                                            
                                            # Get the full CV data
                                            cv_data = get_cv_by_id(db_manager, cv_id)
                                            
                                            # Set as selected CV
                                            selected_cv = cv_id
                                            
                                            st.success(f"CV '{cv_name}' uploaded and parsed successfully!")
            else:
                # No existing CVs, must upload new one
                st.info("You don't have any CVs uploaded yet. Please upload one to continue.")
                
                cv_file = st.file_uploader(
                    "Upload your CV (PDF, DOCX, or TXT)",
                    type=["pdf", "docx", "txt"],
                    key="cv_uploader"
                )
                
                cv_name = st.text_input("CV Name", placeholder="Give your CV a name")
                
                if cv_file and cv_name:
                    with st.spinner("Extracting text from CV..."):
                        cv_text = extract_text_from_file(cv_file, error_tracker)
                        
                        if cv_text:
                            # Save CV to database
                            success, cv_id = save_cv(db_manager, st.session_state['user_id'], cv_name, cv_text)
                            
                            if success:
                                # Parse CV
                                with st.spinner("Parsing CV..."):
                                    parsed_data = parse_cv(client, cv_text, cv_name, error_tracker)
                                    
                                    if parsed_data:
                                        # Update CV with parsed data
                                        update_cv_parsed_data(db_manager, cv_id, parsed_data)
                                        
                                        # Get the full CV data
                                        cv_data = get_cv_by_id(db_manager, cv_id)
                                        
                                        # Set as selected CV
                                        selected_cv = cv_id
                                        
                                        st.success(f"CV '{cv_name}' uploaded and parsed successfully!")
            st.markdown('</div>', unsafe_allow_html=True)
        
        # Analysis button
        analyze_col1, analyze_col2, analyze_col3 = st.columns([1, 2, 1])
        with analyze_col2:
            # Check if we have all required data
            can_analyse = (
                'selected_cv' in locals() and 
                selected_cv and 
                job_description and
                len(job_description.strip()) > 50
            )
            
            if st.button(
                "Analyse CV Match", 
                type="primary",
                disabled=not can_analyse,
                use_container_width=True
            ):
                if can_analyse:
                    # Get the CV data
                    cv_data = get_cv_by_id(db_manager, selected_cv)
                    
                    if cv_data:
                        # Create progress container
                        progress_container = st.container()
                        
                        with progress_container:
                            progress_bar = st.progress(0.0)
                            status_text = st.empty()
                            
                            # Save job description
                            status_text.text("Saving job description...")
                            success, job_description_id = save_job_description(
                                db_manager,
                                st.session_state['user_id'],
                                job_title or "Untitled Position",
                                company or "",
                                job_description
                            )
                            progress_bar.progress(0.15)
                            
                            if success:
                                # Analyse match
                                status_text.text("Analysing CV match with job description...")
                                analysis_results = analyze_cv_match(client, cv_data, job_description, error_tracker)
                                progress_bar.progress(0.85)
                                
                                if analysis_results:
                                    # Save analysis results
                                    status_text.text("Saving analysis results...")
                                    match_score = analysis_results.get('match_score', 0)
                                    save_success, analysis_id = save_analysis_result(
                                        db_manager,
                                        st.session_state['user_id'],
                                        selected_cv,
                                        job_description_id,
                                        match_score,
                                        analysis_results
                                    )
                                    progress_bar.progress(1.0)
                                    
                                    if save_success:
                                        # Store in session state
                                        st.session_state['current_analysis_id'] = analysis_id
                                        
                                        # Redirect to analysis results
                                        status_text.success("Analysis complete! View your results in the 'My Analyses' tab.")
                                        st.session_state['show_analysis_tab'] = True
                                        st.rerun()
                                    else:
                                        status_text.error("Failed to save analysis results. Please try again.")
                                else:
                                    status_text.error("Failed to analyse CV match. Please try again.")
                            else:
                                status_text.error("Failed to save job description. Please try again.")
        
        # Display any errors that were tracked
        error_tracker.display_errors()
    
    # MY CVS TAB
    with dashboard_tabs[1]:
        st.header("My CVs")
        
        # Get user's CVs
        user_cvs = get_user_cvs(db_manager, st.session_state['user_id'])
        
        # Upload new CV button
        with st.expander("Upload New CV", expanded=not user_cvs):
            col1, col2 = st.columns(2)
            
            with col1:
                cv_file = st.file_uploader(
                    "Upload your CV (PDF, DOCX, or TXT)",
                    type=["pdf", "docx", "txt"],
                    key="cv_uploader_tab"
                )
            
            with col2:
                cv_name = st.text_input("CV Name", placeholder="Give your CV a name", key="cv_name_tab")
                
                if st.button("Upload CV", disabled=not (cv_file and cv_name)):
                    with st.spinner("Extracting text from CV..."):
                        cv_text = extract_text_from_file(cv_file, error_tracker)
                        
                        if cv_text:
                            # Save CV to database
                            success, cv_id = save_cv(db_manager, st.session_state['user_id'], cv_name, cv_text)
                            
                            if success:
                                # Parse CV
                                with st.spinner("Parsing CV..."):
                                    parsed_data = parse_cv(client, cv_text, cv_name, error_tracker)
                                    
                                    if parsed_data:
                                        # Update CV with parsed data
                                        update_cv_parsed_data(db_manager, cv_id, parsed_data)
                                        st.success(f"CV '{cv_name}' uploaded and parsed successfully!")
                                        st.rerun()
        
        # Display existing CVs
        if user_cvs:
            st.subheader(f"Your CVs ({len(user_cvs)})")
            
            # Create a grid of cards for CVs
            for i in range(0, len(user_cvs), 2):
                cols = st.columns(2)
                
                for j in range(2):
                    if i + j < len(user_cvs):
                        cv = user_cvs[i + j]
                        
                        with cols[j]:
                            st.markdown('<div class="card">', unsafe_allow_html=True)
                            st.markdown(f"### {cv['cv_name']}")
                            st.markdown(f"Uploaded: {cv['upload_date'].strftime('%d %b %Y')}")
                            
                            # Check if CV has been parsed
                            if cv.get('parsed_data'):
                                with st.expander("View CV Summary"):
                                    display_cv_summary(cv)
                            else:
                                with st.spinner("Parsing CV..."):
                                    # Parse CV if not already parsed
                                    parsed_data = parse_cv(client, cv['cv_text'], cv['cv_name'], error_tracker)
                                    
                                    if parsed_data:
                                        # Update CV with parsed data
                                        update_cv_parsed_data(db_manager, cv['cv_id'], parsed_data)
                                        cv['parsed_data'] = parsed_data
                                        
                                        with st.expander("View CV Summary"):
                                            display_cv_summary(cv)
                            
                            # Action buttons
                            col1, col2 = st.columns(2)
                            
                            with col1:
                                if st.button("Use for Analysis", key=f"use_{cv['cv_id']}"):
                                    # Switch to analysis tab with this CV selected
                                    st.session_state['selected_cv_id'] = cv['cv_id']
                                    st.session_state['show_analysis_tab'] = True
                                    st.rerun()
                            
                            with col2:
                                if st.button("Delete CV", key=f"delete_{cv['cv_id']}"):
                                    # Delete confirmation
                                    if st.checkbox(f"Confirm deletion of '{cv['cv_name']}'", key=f"confirm_{cv['cv_id']}"):
                                        # First check if CV is used in any analyses
                                        analyses = db_manager.execute_query(
                                            "SELECT * FROM analyses WHERE cv_id = %s",
                                            (cv['cv_id'],)
                                        )
                                        
                                        if analyses:
                                            # Delete related analyses first
                                            db_manager.execute_query(
                                                "DELETE FROM analyses WHERE cv_id = %s",
                                                (cv['cv_id'],),
                                                fetch=False
                                            )
                                        
                                        # Delete CV
                                        db_manager.execute_query(
                                            "DELETE FROM cvs WHERE cv_id = %s",
                                            (cv['cv_id'],),
                                            fetch=False
                                        )
                                        
                                        st.success(f"CV '{cv['cv_name']}' deleted successfully!")
                                        st.rerun()
                            st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.info("You don't have any CVs uploaded yet. Please upload one using the form above.")
    
    # MY ANALYSES TAB
    with dashboard_tabs[2]:
        st.header("My Analyses")
        
        # Show analysis tab if coming from analyse button
        if st.session_state.get('show_analysis_tab', False):
            st.session_state['show_analysis_tab'] = False
            
            if 'current_analysis_id' in st.session_state:
                # Get the analysis
                analysis_data = get_analysis_by_id(db_manager, st.session_state['current_analysis_id'])
                
                if analysis_data:
                    # Display analysis results
                    st.subheader(f"Analysis Results: {analysis_data['job_title']}")
                    
                    # Convert JSON data
                    analysis = analysis_data['analysis_data']
                    
                    # Main score section
                    st.markdown('<div class="card">', unsafe_allow_html=True)
                    score_col1, score_col2 = st.columns([1, 3])
                    
                    with score_col1:
                        match_score = analysis.get('match_score', 0)
                        display_match_score(match_score)
                    
                    with score_col2:
                        # Skill assessment visualization
                        st.subheader("Skills Assessment")
                        skills_assessment = analysis.get('skills_assessment', {})
                        
                        skills_chart = create_skills_chart(skills_assessment)
                        if skills_chart:
                            st.altair_chart(skills_chart, use_container_width=True)
                    st.markdown('</div>', unsafe_allow_html=True)
                    
                    # Strengths and improvement areas
                    display_strengths_and_improvements(
                        strengths=analysis.get('strengths', []), 
                        improvements=analysis.get('improvement_areas', [])
                    )
                    
                    # Detailed analysis tabs
                    analysis_detail_tabs = st.tabs([
                        "Recommendations", "Keywords", "Cover Letter", "Interview Tips"
                    ])
                    
                    with analysis_detail_tabs[0]:
                        # Recommendations
                        display_recommendations(analysis.get('recommendations', []))
                        
                        # Experience Gap Analysis
                        st.markdown('<div class="card">', unsafe_allow_html=True)
                        st.subheader("Experience Gap Analysis")
                        experience_gaps = analysis.get('experience_gap_analysis', [])
                        if experience_gaps:
                            for gap in experience_gaps:
                                st.markdown(f"🔸 **{gap}**")
                        else:
                            st.markdown("*No specific experience gaps identified.*")
                        st.markdown('</div>', unsafe_allow_html=True)
                    
                    with analysis_detail_tabs[1]:
                        # Keyword Analysis
                        st.markdown('<div class="card">', unsafe_allow_html=True)
                        keywords = analysis.get('keyword_analysis', [])
                        display_keywords(keywords, max_cols=3)
                        st.markdown('</div>', unsafe_allow_html=True)
                        
                        # Potential Alternative Job Titles
                        st.markdown('<div class="card">', unsafe_allow_html=True)
                        st.subheader("Alternative Job Titles to Consider")
                        alt_titles = analysis.get('potential_job_titles', [])
                        if alt_titles:
                            st.markdown("Based on your CV, you might also be a good fit for these roles:")
                            for title in alt_titles:
                                st.markdown(f"🔹 **{title}**")
                        else:
                            st.markdown("*No alternative job titles suggested.*")
                        st.markdown('</div>', unsafe_allow_html=True)
                    
                    with analysis_detail_tabs[2]:
                        # Generate cover letter
                        st.markdown('<div class="card">', unsafe_allow_html=True)
                        st.subheader("Custom Cover Letter")
                        
                        if st.button("Generate Cover Letter"):
                            with st.spinner("Generating your personalised cover letter..."):
                                cover_letter = generate_cover_letter(
                                    client,
                                    {'parsed_data': analysis_data['cv_parsed_data']},
                                    analysis_data['description_text'],
                                    analysis
                                )
                                
                                if cover_letter:
                                    st.markdown("### Your Cover Letter")
                                    st.markdown(cover_letter)
                                    
                                    # Download button
                                    st.download_button(
                                        label="Download Cover Letter",
                                        data=cover_letter,
                                        file_name=f"cover_letter_{analysis_data['job_title'].replace(' ', '_')}.txt",
                                        mime="text/plain"
                                    )
                        st.markdown('</div>', unsafe_allow_html=True)
                    
                    with analysis_detail_tabs[3]:
                        # Generate interview tips
                        st.markdown('<div class="card">', unsafe_allow_html=True)
                        st.subheader("Interview Preparation Tips")
                        
                        if st.button("Generate Interview Tips"):
                            with st.spinner("Generating personalised interview tips..."):
                                interview_tips = generate_interview_tips(
                                    client,
                                    {'parsed_data': analysis_data['cv_parsed_data']},
                                    analysis_data['description_text'],
                                    analysis
                                )
                                
                                if interview_tips:
                                    st.markdown("### Your Interview Tips")
                                    st.markdown(interview_tips)
                        st.markdown('</div>', unsafe_allow_html=True)
        
        # Show all user analyses
        st.subheader("All Your Analyses")
        user_analyses = get_user_analyses(db_manager, st.session_state['user_id'])
        
        if user_analyses:
            for analysis in user_analyses:
                st.markdown('<div class="card">', unsafe_allow_html=True)
                
                # Analysis header
                col1, col2, col3 = st.columns([3, 1, 1])
                
                with col1:
                    st.markdown(f"### {analysis['job_title']}")
                    if analysis.get('company'):
                        st.markdown(f"**Company:** {analysis['company']}")
                    st.markdown(f"**CV:** {analysis['cv_name']}")
                    
                with col2:
                    match_score = analysis['match_score']
                    if match_score >= 80:
                        color = "green"
                    elif match_score >= 60:
                        color = "orange"
                    else:
                        color = "red"
                    st.markdown(f"**Match Score:** <span style='color: {color}; font-weight: bold;'>{match_score}%</span>", unsafe_allow_html=True)
                
                with col3:
                    if st.button("View Details", key=f"view_{analysis['analysis_id']}"):
                        st.session_state['current_analysis_id'] = analysis['analysis_id']
                        st.session_state['show_analysis_tab'] = True
                        st.rerun()
                
                # Analysis date
                st.markdown(f"*Analysed on {analysis['created_at'].strftime('%d %b %Y at %H:%M')}*")
                
                st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.info("You haven't performed any analyses yet. Use the 'Analyse New Job' tab to get started!")
    
    # MY ACCOUNT TAB
    with dashboard_tabs[3]:
        st.header("My Account")
        
        if user_data:
            # Account information
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.subheader("Account Information")
            
            # Display user info
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown(f"**Full Name:** {user_data.get('full_name', 'Not provided')}")
                st.markdown(f"**Email:** {user_data.get('email', 'Not provided')}")
                st.markdown(f"**Member Since:** {user_data.get('created_at', 'Unknown').strftime('%B %Y') if user_data.get('created_at') else 'Unknown'}")
            
            with col2:
                # Subscription info
                if user_data.get('subscription_status') == 'active' and user_data.get('subscription_end') and user_data.get('subscription_end') > datetime.now():
                    days_left = (user_data['subscription_end'] - datetime.now()).days
                    st.success(f"✅ Active Subscription ({days_left} days remaining)")
                    st.markdown(f"**Subscription End:** {user_data['subscription_end'].strftime('%d %B %Y')}")
                else:
                    st.error("❌ No Active Subscription")
                    
                    if st.button("Subscribe Now", key="account_subscribe"):
                        try:
                            with st.spinner("Creating checkout session..."):
                                checkout_session = create_stripe_checkout_session(
                                    user_data['user_id'],
                                    user_data['email']
                                )
                                
                                if checkout_session and checkout_session.url:
                                    st.session_state['checkout_url'] = checkout_session.url
                                    st.rerun()
                                else:
                                    st.error("Failed to create checkout session. Please try again.")
                        except Exception as e:
                            st.error(f"Failed to create checkout session: {str(e)}")
            
            st.markdown('</div>', unsafe_allow_html=True)
            
            # Usage statistics
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.subheader("Usage Statistics")
            
            # Get user's usage stats
            user_analyses_count = len(get_user_analyses(db_manager, user_data['user_id']))
            user_cvs_count = len(get_user_cvs(db_manager, user_data['user_id']))
            
            # Token usage
            token_usage = db_manager.execute_query(
                """
                SELECT SUM(tokens_used) as total_tokens, COUNT(*) as request_count
                FROM token_usage
                WHERE user_id = %s
                """,
                (user_data['user_id'],)
            )
            
            # Display stats
            stats_col1, stats_col2, stats_col3 = st.columns(3)
            
            with stats_col1:
                st.metric("CVs Uploaded", user_cvs_count)
            
            with stats_col2:
                st.metric("Analyses Performed", user_analyses_count)
            
            with stats_col3:
                total_tokens = token_usage[0]['total_tokens'] if token_usage and token_usage[0]['total_tokens'] else 0
                st.metric("AI Tokens Used", f"{total_tokens:,}")
            
            st.markdown('</div>', unsafe_allow_html=True)
            
            # Account actions
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.subheader("Account Actions")
            
            # Change password (simplified - in production you'd want email verification)
            with st.expander("Change Password"):
                with st.form("change_password_form"):
                    current_password = st.text_input("Current Password", type="password")
                    new_password = st.text_input("New Password", type="password")
                    confirm_new_password = st.text_input("Confirm New Password", type="password")
                    
                    if st.form_submit_button("Change Password"):
                        if not current_password or not new_password or not confirm_new_password:
                            st.error("Please fill in all fields.")
                        elif new_password != confirm_new_password:
                            st.error("New passwords do not match.")
                        elif len(new_password) < 6:
                            st.error("New password must be at least 6 characters long.")
                        else:
                            # Verify current password
                            if bcrypt.checkpw(current_password.encode('utf-8'), user_data['password_hash'].encode('utf-8')):
                                # Hash new password
                                new_password_hash = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                                
                                # Update password in database
                                success = db_manager.execute_query(
                                    "UPDATE users SET password_hash = %s WHERE user_id = %s",
                                    (new_password_hash, user_data['user_id']),
                                    fetch=False
                                )
                                
                                if success:
                                    st.success("Password changed successfully!")
                                else:
                                    st.error("Failed to change password. Please try again.")
                            else:
                                st.error("Current password is incorrect.")
            
            # Export data
            with st.expander("Export Your Data"):
                st.markdown("Download all your CareerVertex data including CVs and analyses.")
                
                if st.button("Export Data"):
                    # Collect all user data
                    export_data = {
                        "user_info": {
                            "email": user_data['email'],
                            "full_name": user_data.get('full_name'),
                            "member_since": user_data.get('created_at').isoformat() if user_data.get('created_at') else None
                        },
                        "cvs": get_user_cvs(db_manager, user_data['user_id']),
                        "analyses": get_user_analyses(db_manager, user_data['user_id'])
                    }
                    
                    # Convert to JSON
                    export_json = json.dumps(export_data, indent=2, default=str)
                    
                    # Provide download
                    st.download_button(
                        label="Download Data (JSON)",
                        data=export_json,
                        file_name=f"careervertex_data_{user_data['email']}.json",
                        mime="application/json"
                    )
            
            # Delete account
            with st.expander("⚠️ Delete Account"):
                st.warning("This action cannot be undone. All your data will be permanently deleted.")
                
                delete_confirmation = st.text_input("Type 'DELETE' to confirm account deletion")
                
                if st.button("Delete My Account", type="primary") and delete_confirmation == "DELETE":
                    # Delete all user data
                    user_id = user_data['user_id']
                    
                    # Delete in reverse order of foreign key dependencies
                    db_manager.execute_query("DELETE FROM token_usage WHERE user_id = %s", (user_id,), fetch=False)
                    db_manager.execute_query("DELETE FROM analyses WHERE user_id = %s", (user_id,), fetch=False)
                    db_manager.execute_query("DELETE FROM job_descriptions WHERE user_id = %s", (user_id,), fetch=False)
                    db_manager.execute_query("DELETE FROM cvs WHERE user_id = %s", (user_id,), fetch=False)
                    db_manager.execute_query("DELETE FROM payments WHERE user_id = %s", (user_id,), fetch=False)
                    db_manager.execute_query("DELETE FROM users WHERE user_id = %s", (user_id,), fetch=False)
                    
                    # Logout user
                    auth_manager.logout_user()
                    st.success("Account deleted successfully. You have been logged out.")
                    st.rerun()
            
            st.markdown('</div>', unsafe_allow_html=True)
