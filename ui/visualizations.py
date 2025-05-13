import streamlit as st
import pandas as pd
import altair as alt

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
