import streamlit as st

def display_match_score(score):
    """Display the match score with appropriate color and text."""
    if score >= 80:
        score_color = "green"
        score_text = "Strong Match!"
    elif score >= 60:
        score_color = "orange"
        score_text = "Good Match"
    else:
        score_color = "red"
        score_text = "Needs Improvement"
        
    # Display overall score with a gauge-like visualization
    st.markdown(f"# :{score_color}[{score}%]")
    st.markdown(f"### :{score_color}[{score_text}]")

def display_strengths_and_improvements(strengths, improvements):
    """Display strengths and improvements in a two-column layout."""
    strengths_col, improve_col = st.columns(2)
    
    with strengths_col:
        st.subheader("Your Strengths")
        if strengths:
            for strength in strengths:
                st.markdown(f"✅ **{strength}**")
        else:
            st.markdown("*No specific strengths identified.*")
            
    with improve_col:
        st.subheader("Areas for Improvement")
        if improvements:
            for area in improvements:
                st.markdown(f"🔍 **{area}**")
        else:
            st.markdown("*No specific improvement areas identified.*")

def display_recommendations(recommendations):
    """Display recommendations with numbered points."""
    st.subheader("Recommendations to Improve Your Application")
    if recommendations:
        for i, rec in enumerate(recommendations):
            st.markdown(f"**{i+1}. {rec}**")
    else:
        st.markdown("*No specific recommendations available.*")

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
                f"""<div style='background-color:var(--background-color);padding:10px;margin:5px;
                border:1px solid var(--primary-color);border-radius:20px;text-align:center;font-weight:500;'>{keyword}</div>""", 
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
                f"""<div style='background-color:var(--background-color);padding:15px;margin:10px;
                border-left:4px solid var(--primary-color);border-radius:5px;'>
                📈 {trend}</div>""", 
                unsafe_allow_html=True
            )
    else:
        st.markdown("*No industry trends identified.*")

def display_resume_summary(resume_data):
    """Display a summary of the parsed resume."""
    if resume_data:
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
    else:
        st.markdown("*No resume data available*")
