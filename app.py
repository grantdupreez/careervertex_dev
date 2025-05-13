import streamlit as st
import pandas as pd
import altair as alt
import numpy as np

# Import utility modules
from utils.error_tracker import error_tracker
from utils.extract_text import extract_text_from_file
from utils.api_client import initialize_anthropic_client

# Import analysis modules
from analysis.resume_parser import parse_resume
from analysis.job_analyzer import analyze_resume_match, generate_interview_tips
from analysis.industry_analyzer import analyze_industry_fit
from analysis.report_generator import generate_comprehensive_report, generate_cover_letter
from analysis.trend_analyzer import store_analysis_history, generate_trend_charts
from analysis.report_generator import generate_comprehensive_report, generate_cover_letter, generate_tailored_resume

# Import UI modules
from ui.auth import check_password
from ui.components import (
    display_match_score, display_strengths_and_improvements,
    display_recommendations, display_keywords, display_trends, 
    display_resume_summary
)
from ui.visualizations import create_skills_chart

# --- App Setup ---
st.set_page_config(page_title="CareerVertex - Resume Job Match Analyser", layout="wide")
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
           'industry_analysis', 'comprehensive_report', 'cover_letter', 'tailored_resume']:
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

with col2:
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
        
        # Strengths and improvement areas
        st.markdown("---")
        strengths = analysis_results.get('strengths', [])
        improvements = analysis_results.get('improvement_areas', [])
        display_strengths_and_improvements(strengths, improvements)
        
        # Quick action buttons
        st.markdown("---")
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
            if st.button("Tailor Resume", use_container_width=True):
                with st.spinner("Creating your tailored resume..."):
                    tailored_resume = generate_tailored_resume(client, resume_data, job_description, analysis_results)
                    st.session_state['tailored_resume'] = tailored_resume
                    st.success("Tailored resume created! Check the Full Report tab.")
    
    # DETAILS TAB
    with details_tab:
        st.header("Detailed Analysis")
        
        # Display interview tips if requested
        if st.session_state.get('show_interview_tips', False):
            st.subheader("Interview Preparation Tips")
            interview_tips = st.session_state.get('interview_tips')
            if interview_tips and isinstance(interview_tips, str):
                st.markdown(interview_tips)
            elif interview_tips and isinstance(interview_tips, list):
                for tip in interview_tips:
                    st.markdown(tip)
            else:
                st.markdown("*Unable to generate interview tips.*")
        
        # Recommendations section
        recommendations = analysis_results.get('recommendations', [])
        display_recommendations(recommendations)
        
        # Keyword Analysis - improved display
        keywords = analysis_results.get('keyword_analysis', [])
        display_keywords(keywords, max_cols=3)
        
        # Experience Gap Analysis - new section
        st.subheader("Experience Gap Analysis")
        experience_gaps = analysis_results.get('experience_gap_analysis', [])
        if experience_gaps:
            for gap in experience_gaps:
                st.markdown(f"🔸 **{gap}**")
        else:
            st.markdown("*No specific experience gaps identified.*")
            
        # Potential Alternative Job Titles - new section
        st.subheader("Alternative Job Titles to Consider")
        alt_titles = analysis_results.get('potential_job_titles', [])
        if alt_titles:
            st.markdown("Based on your resume, you might also be a good fit for these roles:")
            for title in alt_titles:
                st.markdown(f"🔹 **{title}**")
        else:
            st.markdown("*No alternative job titles suggested.*")
    
    # INDUSTRY TAB
    with industry_tab:
        st.header("Industry Insights")
        
        if industry_analysis:
            # Industry overview
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
            
            # Current trends section with improved styling
            st.markdown("---")
            st.subheader("Current Industry Trends")
            trends = industry_analysis.get('industry_trends', [])
            display_trends(trends, max_cols=2)
            
            # Industry challenges section
            st.markdown("---")
            st.subheader("Current Industry Challenges")
            challenges = industry_analysis.get('industry_challenges', [])
            if challenges:
                for challenge in challenges:
                    st.markdown(f"⚠️ **{challenge}**")
            else:
                st.markdown("*No industry challenges identified.*")
            
            # Industry keywords
            st.markdown("---")
            st.subheader("Industry-Specific Keywords")
            st.markdown("*Adding these industry-specific keywords to your resume could improve your chances:*")
            
            ind_keywords = industry_analysis.get('industry_keywords', [])
            display_keywords(ind_keywords, max_cols=3)
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
                # Match score trend
                st.subheader("Application Match Score Trend")
                st.altair_chart(charts.get('match_score'), use_container_width=True)
                
                # Skills comparison across jobs
                if 'skills' in charts:
                    st.subheader("Skills Assessment Across Applications")
                    st.altair_chart(charts.get('skills'), use_container_width=True)
                
                # Analysis and insights
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
            else:
                st.warning("Unable to generate trend charts with the available data.")
        else:
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
    
    # REPORT TAB
    with report_tab:
        st.header("Comprehensive Report")
        
        # Calculate and display token count for the report
        comprehensive_report = st.session_state.get('comprehensive_report')
        if comprehensive_report:
            report_tokens = len(comprehensive_report.split())
            st.info(f"Report length: {report_tokens} tokens")
        
        # Cover letter section
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

        # Tailored resume section
        if 'tailored_resume' in st.session_state and st.session_state['tailored_resume']:
            with st.expander("Your Tailored Resume", expanded=True):
                st.markdown(st.session_state['tailored_resume'])
                
                # Add option to download tailored resume
                tailored_resume_text = st.session_state['tailored_resume']
                st.download_button(
                    label="Download Tailored Resume",
                    data=tailored_resume_text,
                    file_name="tailored_resume.md",
                    mime="text/markdown"
                )
        else:
            # Button to generate tailored resume
            if st.button("Generate Tailored Resume"):
                with st.spinner("Creating your tailored resume..."):
                    tailored_resume = generate_tailored_resume(client, resume_data, job_description, analysis_results)
                    st.session_state['tailored_resume'] = tailored_resume
                    st.rerun()
        
        # Full report
        if comprehensive_report:
            with st.expander("Full Analysis Report", expanded=True):
                st.markdown(comprehensive_report)
                
                # Offer download
                st.download_button(
                    label="Download Full Report as Markdown",
                    data=comprehensive_report,
                    file_name="resume_analysis_report.md",
                    mime="text/markdown"
                )
        
        # Resume summary
        with st.expander("Your Resume Summary"):
            display_resume_summary(resume_data)
    
        # Data retention policy
        with st.expander("Data Retention Policy"):
            st.markdown("""
            ### How We Handle Your Data
            
            - **Session-Based Storage**: Your data is only stored in your current browser session
            - **No External Database**: We don't save your resume or job descriptions to any external database
            - **No Data Sharing**: Your information is not shared with third parties
            - **Automatic Cleanup**: All data is automatically erased when you close your browser tab
            
            To manually delete all data, click the "Reset & Analyse Another Resume" button or close this tab.
            """)

# Footer
st.markdown("### How to Use This Analysis")
st.markdown("""
1. **Review your match score** to understand your overall fit for the position
2. **Focus on improving areas** identified in the analysis
3. **Add missing keywords** to your resume for better ATS matching
4. **Use industry insights** to better tailor your application to the specific field
5. **Generate a tailored resume** that's optimized for this specific job application
6. **Prepare for interviews** using the provided tips
7. **Use the generated cover letter** to create a tailored application highlighting your strengths
8. **Track your progress** across multiple job applications with the trend analysis
9. **Download the full report** for your records or to discuss with a career counselor
""")

st.markdown("---")
st.markdown("Powered by Claude AI")
st.caption("This tool uses AI to provide resume analysis and should be used as a guide only. Final decisions should always be made by human recruiters.")
