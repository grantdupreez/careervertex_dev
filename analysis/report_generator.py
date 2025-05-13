from datetime import datetime
import json
from utils.error_tracker import error_tracker
from utils.api_client import call_anthropic_api_with_timeout

def generate_tailored_resume(client, resume_data, job_description, analysis):
    """
    Generates a tailored version of the resume optimized for the specific job description.
    """
    if not resume_data or not job_description or not analysis:
        return "Unable to generate tailored resume due to missing data."
    
    # Extract key information to customize the resume
    candidate_name = resume_data.get('name', 'Candidate')
    strengths = analysis.get('strengths', [])
    keywords = analysis.get('keyword_analysis', [])
    
    # Convert data to JSON for the prompt
    try:
        resume_json = json.dumps(resume_data, indent=2)
        analysis_json = json.dumps(analysis, indent=2)
    except Exception as e:
        error_tracker.add_error("json_error", "Error preparing data for tailored resume", False, str(e))
        return "Error generating tailored resume."
    
    prompt = f"""
    You are an expert resume writer. Based on this candidate's resume and the job description analysis, 
    create a tailored version of their resume that highlights relevant qualifications and 
    addresses the gaps identified in the analysis.

    Job Description:
    ---
    {job_description}
    ---

    Original Resume Data (JSON):
    ---
    {resume_json}
    ---
    
    Resume Analysis:
    ---
    {analysis_json}
    ---

    Create a thoroughly tailored version of this resume that:

    1. Maintains the candidate's accurate work history, education, and skills
    2. Reorganizes and rephrases content to emphasize experiences relevant to this specific job
    3. Incorporates the missing keywords from the job description naturally
    4. Enhances sections that align with the identified strengths
    5. Addresses the improvement areas and experience gaps where possible
    6. Uses industry-specific terminology that's relevant to the role
    7. Follows best practices for ATS optimization
    8. Keeps a professional, clean format
    9. Uses bullet points effectively to highlight achievements and responsibilities
    10. Quantifies accomplishments where possible

    Format the resume in a clean, modern style with clear section headings. 
    Use British English spelling and grammar conventions.
    The result should be a complete, ready-to-use resume in Markdown format.
    """

    # Use enhanced API call with timeout
    success, response_text = call_anthropic_api_with_timeout(
        client=client,
        prompt=prompt,
        max_tokens=3000,
        temperature=0.3,
        system="You are a professional resume writer specializing in creating tailored, ATS-optimized resumes. Create a tailored resume that addresses the specific job requirements while maintaining accuracy about the candidate's background.",
        timeout=60,
        retries=1
    )
    
    if not success:
        return "Unable to generate tailored resume. Please try again later."
    
    # Return the tailored resume text directly
    return response_text

def generate_comprehensive_report(resume_data, job_description, analysis, industry_analysis):
    """
    Generates a detailed PDF-ready report with all analyses.
    """
    # For now, we'll generate a structured markdown report that can be saved
    report_parts = []
    
    # Title and header
    report_parts.append(f"# Resume Analysis Report\n")
    report_parts.append(f"**Candidate:** {resume_data.get('name', 'Candidate')}\n")
    report_parts.append(f"**Date:** {datetime.now().strftime('%B %d, %Y')}\n")
    report_parts.append(f"**Match Score:** {analysis.get('match_score', 0)}%\n")
    
    # Executive summary
    report_parts.append("## Executive Summary\n")
    strengths = analysis.get('strengths', [])
    if strengths:
        report_parts.append("### Key Strengths\n")
        for strength in strengths:
            report_parts.append(f"- {strength}\n")
    
    improvement_areas = analysis.get('improvement_areas', [])
    if improvement_areas:
        report_parts.append("\n### Areas for Improvement\n")
        for area in improvement_areas:
            report_parts.append(f"- {area}\n")
    
    # Detailed Skills Assessment
    report_parts.append("\n## Skills Assessment\n")
    skills = analysis.get('skills_assessment', {})
    for skill, rating in skills.items():
        report_parts.append(f"- **{skill}:** {rating}/100\n")
    
    # Industry Analysis
    if industry_analysis:
        report_parts.append("\n## Industry Analysis\n")
        report_parts.append(f"- **Industry:** {industry_analysis.get('industry_identified', 'Unknown')}\n")
        report_parts.append(f"- **Industry Fit:** {industry_analysis.get('industry_fit_score', 0)}/100\n")
        
        industry_trends = industry_analysis.get('industry_trends', [])
        if industry_trends:
            report_parts.append("\n### Industry Trends\n")
            for trend in industry_trends:
                report_parts.append(f"- {trend}\n")
                
        industry_keywords = industry_analysis.get('industry_keywords', [])
        if industry_keywords:
            report_parts.append("\n### Key Industry Terms\n")
            for keyword in industry_keywords:
                report_parts.append(f"- {keyword}\n")
                
        industry_challenges = industry_analysis.get('industry_challenges', [])
        if industry_challenges:
            report_parts.append("\n### Industry Challenges\n")
            for challenge in industry_challenges:
                report_parts.append(f"- {challenge}\n")
                
        competitors = industry_analysis.get('competitors', [])
        if competitors:
            report_parts.append("\n### Key Competitors\n")
            for competitor in competitors:
                report_parts.append(f"- {competitor}\n")
                
        salary_range = industry_analysis.get('salary_range', {})
        if salary_range and salary_range.get('min', 0) > 0:
            report_parts.append(f"\n**Typical Salary Range:** £{salary_range.get('min', 0):,} - £{salary_range.get('max', 0):,}\n")
    
    # Keyword Analysis
    keywords = analysis.get('keyword_analysis', [])
    if keywords:
        report_parts.append("\n## Keyword Analysis\n")
        report_parts.append("Keywords that appear in the job description but are missing or underemphasised in your resume:\n")
        for keyword in keywords:
            report_parts.append(f"- {keyword}\n")
    
    # Experience Gap Analysis
    experience_gaps = analysis.get('experience_gap_analysis', [])
    if experience_gaps:
        report_parts.append("\n## Experience Gap Analysis\n")
        for gap in experience_gaps:
            report_parts.append(f"- {gap}\n")
    
    # Recommendations
    recommendations = analysis.get('recommendations', [])
    if recommendations:
        report_parts.append("\n## Recommendations\n")
        for i, rec in enumerate(recommendations):
            report_parts.append(f"{i+1}. {rec}\n")
    
    # Final Notes
    report_parts.append("\n## Next Steps\n")
    report_parts.append("1. Update your resume based on the recommendations above\n")
    report_parts.append("2. Prepare for interviews using the interview tips provided separately\n")
    report_parts.append("3. Research the industry trends and competitors identified\n")
    report_parts.append("4. Consider applying for the alternate job titles suggested if appropriate\n")
    
    # Join all parts
    return "".join(report_parts)

def generate_cover_letter(client, resume_data, job_description, analysis):
    """
    Generates a customised cover letter based on resume, job description, and match analysis.
    """
    if not resume_data or not job_description or not analysis:
        return "Unable to generate cover letter due to missing data."
    
    # Extract key information to personalise the cover letter
    candidate_name = resume_data.get('name', 'Candidate')
    strengths = analysis.get('strengths', [])
    keywords = analysis.get('keyword_analysis', [])
    skills_assessment = analysis.get('skills_assessment', {})
    
    # Convert data to JSON for the prompt
    try:
        resume_json = json.dumps(resume_data, indent=2)
        analysis_json = json.dumps(analysis, indent=2)
    except Exception as e:
        error_tracker.add_error("json_error", "Error preparing data for cover letter", False, str(e))
        return "Error generating cover letter."
    
    prompt = f"""
    You are an expert career consultant. Based on this candidate's resume and the job description analysis, 
    create a professional cover letter that highlights their relevant qualifications and fit for the role.

    Job Description:
    ---
    {job_description}
    ---

    Resume Data:
    ---
    {resume_json}
    ---
    
    Resume Analysis:
    ---
    {analysis_json}
    ---

    Write a complete, professional cover letter that:
    1. Includes a proper salutation (use "Dear Hiring Manager" if no specific recipient is known)
    2. Has an engaging introduction that mentions the specific role they're applying for
    3. Highlights 2-3 of the candidate's key strengths and qualifications that match the job requirements
    4. Uses specific examples from their experience to demonstrate these qualifications
    5. Addresses any potential gaps or concerns tactfully (if relevant)
    6. Incorporates relevant keywords from the job description naturally
    7. Expresses enthusiasm for the role and organisation
    8. Includes a strong closing paragraph with a call to action
    9. Uses a professional sign-off

    The cover letter should be 3-4 paragraphs, professional in tone but conversational, and tailored specifically to this candidate and position.
    Use British English spelling and grammar conventions.
    """

    # Use enhanced API call with timeout
    success, response_text = call_anthropic_api_with_timeout(
        client=client,
        prompt=prompt,
        max_tokens=2000,
        temperature=0.3,
        system="You are a professional career consultant specialising in cover letter writing. Create a tailored, effective cover letter using the candidate's strengths and the job requirements.",
        timeout=45,
        retries=1
    )
    
    if not success:
        return "Unable to generate cover letter. Please try again later."
    
    # Return the cover letter text directly
    return response_text
