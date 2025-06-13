import streamlit as st
from core.ai_analysis import AIAnalyzer
from utils.text_extraction import extract_text_from_file
from components.ui_elements import (
    display_score_circle, display_analysis_results,
    display_cv_card, display_keyword_tags
)
import time

def show_dashboard(db_manager, auth_manager):
    """Main user dashboard."""
    user_id = st.session_state.user_id
    user_data = db_manager.get_user_by_id(user_id)
    
    # Header
    col1, col2, col3 = st.columns([3, 1, 1])
    with col1:
        st.markdown(f"<h1>Welcome back, <span class='gold-gradient'>{user_data['full_name']}</span>!</h1>", unsafe_allow_html=True)
    
    with col2:
        if auth_manager.check_subscription(user_id):
            st.markdown("<span class='status-badge status-active'>Pro Active</span>", unsafe_allow_html=True)
        else:
            st.markdown("<span class='status-badge status-inactive'>No Subscription</span>", unsafe_allow_html=True)
    
    with col3:
        if st.button("Logout"):
            for key in ['user_id', 'user_data']:
                if key in st.session_state:
                    del st.session_state[key]
            st.rerun()
    
    # Check subscription
    if not auth_manager.check_subscription(user_id):
        st.warning("Your subscription has expired. Please renew to continue using CareerVertex.")
        st.stop()
    
    # Main content area
    st.markdown("---")
    
    # Initialize AI analyzer
    ai_analyzer = AIAnalyzer()
    
    # CV Management Section
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.markdown("### Your CVs")
        
        # Get user's CVs
        user_cvs = db_manager.get_user_cvs(user_id)
        
        # Upload new CV
        with st.expander("📤 Upload New CV", expanded=not user_cvs):
            uploaded_file = st.file_uploader(
                "Choose your CV file",
                type=['pdf', 'docx', 'txt'],
                key="cv_upload"
            )
            
            if uploaded_file:
                cv_name = st.text_input("CV Name", value=uploaded_file.name.split('.')[0])
                
                if st.button("Save CV", type="primary"):
                    with st.spinner("Processing your CV..."):
                        # Extract text
                        cv_text = extract_text_from_file(uploaded_file)
                        
                        if cv_text:
                            # Save CV
                            cv_id = db_manager.save_cv(user_id, cv_name, cv_text)
                            
                            if cv_id:
                                # Parse CV immediately
                                parsed_data = ai_analyzer.parse_cv(cv_text, cv_name)
                                if parsed_data:
                                    db_manager.update_cv_parsed_data(cv_id, parsed_data)
                                
                                st.success("CV uploaded and parsed successfully!")
                                time.sleep(1)
                                st.rerun()
                            else:
                                st.error("Failed to save CV")
                        else:
                            st.error("Failed to extract text from file")
        
        # Display existing CVs
        if user_cvs:
            for cv in user_cvs:
                if display_cv_card(cv):
                    st.session_state.selected_cv_id = cv['cv_id']
                    st.rerun()
        else:
            st.info("No CVs uploaded yet")
    
    with col2:
        st.markdown("### Job Analysis")
        
        # Check if CV is selected
        selected_cv_id = st.session_state.get('selected_cv_id')
        
        if selected_cv_id:
            selected_cv = db_manager.get_cv_by_id(selected_cv_id)
            
            if selected_cv:
                st.info(f"Selected CV: **{selected_cv['cv_name']}**")
                
                # Job description input
                tab1, tab2 = st.tabs(["📝 Paste Job Description", "📄 Upload Job Description"])
                
                with tab1:
                    job_description = st.text_area(
                        "Paste the job description here",
                        height=300,
                        placeholder="Copy and paste the complete job description..."
                    )
                    job_title = st.text_input("Job Title", placeholder="e.g., Senior Software Engineer")
                    company = st.text_input("Company (optional)", placeholder="e.g., Google")
                
                with tab2:
                    job_file = st.file_uploader(
                        "Upload job description",
                        type=['pdf', 'docx', 'txt'],
                        key="job_upload"
                    )
                    
                    if job_file:
                        with st.spinner("Extracting text..."):
                            extracted_text = extract_text_from_file(job_file)
                            if extracted_text:
                                job_description = extracted_text
                                st.success("Text extracted successfully!")
                
                # Analysis button
                if job_description and len(job_description.strip()) > 50:
                    if st.button("🚀 Analyze Job Match", type="primary", use_container_width=True):
                        with st.spinner("Analyzing your CV against the job description..."):
                            # Parse job description
                            parsed_job = ai_analyzer.parse_job_description(job_description)
                            
                            # Perform analysis
                            analysis_result = ai_analyzer.analyze_cv_match(
                                selected_cv.get('parsed_data', {}),
                                job_description,
                                parsed_job
                            )
                            
                            if analysis_result:
                                # Save analysis
                                analysis_id = db_manager.save_analysis(
                                    user_id,
                                    selected_cv_id,
                                    job_title or "Untitled Position",
                                    company or "",
                                    job_description,
                                    parsed_job,
                                    analysis_result
                                )
                                
                                if analysis_id:
                                    st.session_state.current_analysis_id = analysis_id
                                    st.success("Analysis complete!")
                                    st.rerun()
                                else:
                                    st.error("Failed to save analysis")
                            else:
                                st.error("Analysis failed. Please try again.")
                else:
                    st.info("Please provide a job description to analyze")
        else:
            st.info("👈 Please select or upload a CV first")
    
    # Analysis Results Section
    if 'current_analysis_id' in st.session_state:
        st.markdown("---")
        
        analysis = db_manager.get_analysis_by_id(st.session_state.current_analysis_id)
        
        if analysis:
            # Clear button
            if st.button("✨ New Analysis", key="clear_analysis"):
                del st.session_state['current_analysis_id']
                st.rerun()
            
            display_analysis_results(analysis, ai_analyzer, db_manager)
    
    # Previous Analyses
    st.markdown("---")
    st.markdown("### Previous Analyses")
    
    user_analyses = db_manager.get_user_analyses(user_id)
    
    if user_analyses:
        # Create a grid of analysis cards
        cols = st.columns(3)
        for idx, analysis in enumerate(user_analyses[:6]):  # Show latest 6
            with cols[idx % 3]:
                st.markdown(f"""
                <div class='card'>
                    <h4>{analysis['job_title']}</h4>
                    <p>{analysis['company'] or 'No company specified'}</p>
                    <p><strong>CV:</strong> {analysis['cv_name']}</p>
                    <p><strong>Score:</strong> {analysis['analysis_result'].get('match_score', 0)}%</p>
                    <p style='font-size: 0.8em; color: #666;'>{analysis['created_at'].strftime('%d %b %Y')}</p>
                </div>
                """, unsafe_allow_html=True)
                
                if st.button("View", key=f"view_{analysis['analysis_id']}"):
                    st.session_state.current_analysis_id = analysis['analysis_id']
                    st.rerun()
    else:
        st.info("No previous analyses found")
