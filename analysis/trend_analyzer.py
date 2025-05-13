import pandas as pd
import altair as alt
import streamlit as st
from datetime import datetime

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
