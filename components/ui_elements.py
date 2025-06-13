import streamlit as st

def display_score_circle(score):
    """Display match score in a circular badge."""
    if score >= 80:
        score_class = "score-high"
        label = "Excellent Match!"
    elif score >= 60:
        score_class = "score-medium"
        label = "Good Match"
    else:
        score_class = "score-low"
        label = "Needs Work"
    
    st.markdown(f"""
    <div style='text-align: center;'>
        <div class='score-circle {score_class}'>
            {score}%
        </div>
        <h3 style='margin-top: 1rem;'>{label}</h3>
    </div>
    """, unsafe_allow_html=True)

def display_cv_card(cv):
    """Display a CV card with selection button."""
    st.markdown(f"""
    <div class='card' style='margin-bottom: 1rem;'>
        <h4 style='margin-bottom: 0.5rem;'>{cv['cv_name']}</h4>
        <p style='font-size: 0.9em; color: #666;'>
            Uploaded: {cv['uploaded_at'].strftime('%d %b %Y')}
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Select", key=f"select_{cv['cv_id']}", use_container_width=True):
            return True
    with col2:
        if st.button("Delete", key=f"delete_{cv['cv_id']}", use_container_width=True):
            # Handle deletion
            pass
    
    return False

def display_keyword_tags(keywords):
    """Display keywords as tags."""
    if not keywords:
        return
    
    tags_html = ""
    for keyword in keywords[:10]:  # Limit to 10 keywords
        tags_html += f"<span class='keyword-tag'>{keyword}</span>"
    
    st.markdown(tags_html, unsafe_allow_html=True)

def display_analysis_results(analysis, ai_analyzer, db_manager):
    """Display comprehensive analysis results."""
    result = analysis['analysis_result']
    
    # Score section
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        display_score_circle(result.get('match_score', 0))
    
    # Key insights
    st.markdown("---")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### ✅ Your Strengths")
        strengths = result.get('strengths', [])
        if strengths:
            for strength in strengths[:5]:
                st.markdown(f"• {strength}")
        else:
            st.markdown("*No specific strengths identified*")
    
    with col2:
        st.markdown("### 🎯 Areas to Improve")
        gaps = result.get('gaps', [])
        if gaps:
            for gap in gaps[:5]:
                st.markdown(f"• {gap}")
        else:
            st.markdown("*No specific gaps identified*")
    
    # Missing keywords
    st.markdown("---")
    st.markdown("### 🔑 Missing Keywords")
    st.markdown("Add these keywords to your CV to improve your match score:")
    display_keyword_tags(result.get('missing_keywords', []))
    
    # Suggestions
    st.markdown("---")
    st.markdown("### 💡 CV Improvement Suggestions")
    
    suggestions = result.get('suggestions', [])
    if suggestions:
        for i, suggestion in enumerate(suggestions, 1):
            st.markdown(f"**{i}.** {suggestion}")
    
    # Action buttons
    st.markdown("---")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("📝 Update CV", use_container_width=True):
            cv_suggestions = ai_analyzer.update_cv_suggestions(
                analysis['cv_data'],
                result
            )
            if cv_suggestions:
                st.session_state.cv_suggestions = cv_suggestions
                st.rerun()
    
    with col2:
        if st.button("✉️ Generate Cover Letter", use_container_width=True):
            with st.spinner("Generating cover letter..."):
                cover_letter = ai_analyzer.generate_cover_letter(
                    analysis['cv_data'],
                    analysis['job_description'],
                    result
                )
                if cover_letter:
                    st.session_state.cover_letter = cover_letter
                    st.rerun()
    
    with col3:
        if st.button("🎤 Interview Tips", use_container_width=True):
            st.session_state.show_interview_tips = True
            st.rerun()
    
    # Show generated content
    if 'cv_suggestions' in st.session_state:
        st.markdown("---")
        st.markdown("### 📋 Specific CV Updates")
        for suggestion in st.session_state.cv_suggestions:
            st.markdown(f"• {suggestion}")
        
        if st.button("Clear Suggestions"):
            del st.session_state['cv_suggestions']
            st.rerun()
    
    if 'cover_letter' in st.session_state:
        st.markdown("---")
        st.markdown("### ✉️ Your Cover Letter")
        st.text_area("Cover Letter", st.session_state.cover_letter, height=400)
        
        col1, col2 = st.columns(2)
        with col1:
            st.download_button(
                "Download Cover Letter",
                st.session_state.cover_letter,
                f"cover_letter_{analysis['job_title'].replace(' ', '_')}.txt",
                "text/plain"
            )
        with col2:
            if st.button("Clear Cover Letter"):
                del st.session_state['cover_letter']
                st.rerun()
    
    if st.session_state.get('show_interview_tips'):
        st.markdown("---")
        st.markdown("### 🎤 Interview Preparation Tips")
        
        tips = result.get('interview_tips', [])
        if tips:
            for i, tip in enumerate(tips, 1):
                st.markdown(f"**Tip {i}:** {tip}")
        else:
            st.markdown("*No specific interview tips available*")
        
        if st.button("Hide Tips"):
            st.session_state.show_interview_tips = False
            st.rerun()
