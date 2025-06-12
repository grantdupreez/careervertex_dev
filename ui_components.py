import streamlit as st
import pandas as pd
import altair as alt
from datetime import datetime
from payment_manager import create_stripe_checkout_session

def create_skills_chart(skills_assessment):
    """Create a horizontal bar chart for skills assessment."""
    if not skills_assessment:
        return None
        
    skill_data = []
    for skill, rating in skills_assessment.items():
        skill_data.append({"Category": skill, "Rating": rating})
        
    if not skill_data:
        return None
        
    skill_df = pd.DataFrame(skill_data)
    
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
    st.markdown("*These keywords appear in the job description but are missing or underemphasised in your CV:*")
    
    if keywords and isinstance(keywords, list):
        keyword_cols = st.columns(max_cols)
        for i, keyword in enumerate(keywords):
            col_idx = i % max_cols
            keyword_cols[col_idx].markdown(
                f'<div class="keyword-tag">{keyword}</div>', 
                unsafe_allow_html=True
            )
    else:
        st.markdown("*No missing keywords identified.*")

def display_cv_summary(cv_data):
    """Display a summary of the parsed CV."""
    if cv_data and 'parsed_data' in cv_data and cv_data['parsed_data']:
        parsed_data = cv_data['parsed_data']
        st.markdown('<div class="card">', unsafe_allow_html=True)
        # Name and contact
        st.markdown(f"### {parsed_data.get('name', 'Candidate')}")
        contact = parsed_data.get('contact_info', {})
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
        skills = parsed_data.get('skills', {})
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
        experience = parsed_data.get('work_experience', [])
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
        education = parsed_data.get('education', [])
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
                    st.markdown(f"- Education entry (format not recognized)")
        else:
            st.markdown("*No education details listed*")
            
        # Certifications
        certifications = parsed_data.get('certifications', [])
        if certifications:
            st.markdown("#### Certifications")
            for cert in certifications:
                st.markdown(f"- {cert}")
        
        st.markdown('</div>', unsafe_allow_html=True)
    elif cv_data:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown(f"### CV: {cv_data.get('cv_name', 'Unnamed CV')}")
        st.markdown(f"**Uploaded:** {cv_data.get('upload_date', 'Unknown date')}")
        
        if cv_data.get('cv_text'):
            with st.expander("View CV Text"):
                st.text(cv_data['cv_text'])
        else:
            st.markdown("*No CV text available*")
        st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.markdown("*No CV data available*")

def display_user_profile(user_data):
    """Display user profile information."""
    if not user_data:
        return
        
    st.markdown('<div class="user-profile">', unsafe_allow_html=True)
    cols = st.columns([1, 4])
    
    with cols[0]:
        # Display user avatar with initials
        initials = ""
        if user_data.get('full_name'):
            name_parts = user_data['full_name'].split()
            initials = "".join([part[0].upper() for part in name_parts if part])[:2]
        else:
            initials = user_data.get('email', '?')[0].upper()
            
        st.markdown(f'<div class="user-avatar">{initials}</div>', unsafe_allow_html=True)
        
    with cols[1]:
        # Display user info
        st.markdown(f"### {user_data.get('full_name', 'User')}")
        st.markdown(f"**Email:** {user_data.get('email', 'No email')}")
        
        # Subscription status
        if user_data.get('subscription_status') == 'active' and user_data.get('subscription_end') and user_data.get('subscription_end') > datetime.now():
            days_left = (user_data['subscription_end'] - datetime.now()).days
            st.markdown(f'<span class="subscription-badge">Active Subscription • {days_left} days left</span>', unsafe_allow_html=True)
        elif user_data.get('subscription_status') == 'active':
            st.markdown(f'<span class="subscription-badge expired">Subscription Expired</span>', unsafe_allow_html=True)
        else:
            st.markdown(f'<span class="subscription-badge expired">No Active Subscription</span>', unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)

def display_pricing():
    """Display pricing information and subscription button."""
    st.markdown("## Subscription")
    
    # Pricing card
    st.markdown('<div class="pricing-card">', unsafe_allow_html=True)
    st.markdown("### CareerVertex Pro")
    st.markdown('<p class="pricing-price">£25<span class="pricing-period">/month</span></p>', unsafe_allow_html=True)
    
    # Features
    st.markdown("#### Features:")
    st.markdown('<div class="feature-item"><i>✓</i> Unlimited CV analyses</div>', unsafe_allow_html=True)
    st.markdown('<div class="feature-item"><i>✓</i> Store multiple CVs and job descriptions</div>', unsafe_allow_html=True)
    st.markdown('<div class="feature-item"><i>✓</i> Compare one CV to multiple job ads</div>', unsafe_allow_html=True)
    st.markdown('<div class="feature-item"><i>✓</i> Industry-specific insights</div>', unsafe_allow_html=True)
    st.markdown('<div class="feature-item"><i>✓</i> Custom cover letter generation</div>', unsafe_allow_html=True)
    st.markdown('<div class="feature-item"><i>✓</i> Interview preparation tips</div>', unsafe_allow_html=True)
    st.markdown('<div class="feature-item"><i>✓</i> Comprehensive reports</div>', unsafe_allow_html=True)
    
    # Subscribe button
    if 'user_id' in st.session_state and 'user_email' in st.session_state:
        if st.button("Subscribe Now", use_container_width=True):
            try:
                checkout_session = create_stripe_checkout_session(
                    st.session_state['user_id'],
                    st.session_state['user_email']
                )
                
                if checkout_session:
                    st.session_state['checkout_url'] = checkout_session.url
                    st.success("Redirecting to payment page...")
                    st.markdown(f'<meta http-equiv="refresh" content="2;URL=\'{checkout_session.url}\'">', unsafe_allow_html=True)
            except Exception as e:
                st.error("Failed to create checkout session. Please try again.")
    else:
        st.info("Please log in to subscribe.")
    
    st.markdown('</div>', unsafe_allow_html=True)