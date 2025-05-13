import json
from utils.error_tracker import error_tracker
from utils.api_client import call_anthropic_api_with_timeout
from utils.json_parser import extract_json_from_string

def analyze_resume_match(client, resume_data, job_description):
    """
    Analyses how well a resume matches with a job description.
    Returns a match analysis with scores and recommendations.
    """
    if not resume_data:
        error_tracker.add_error("parse_error", "No resume data provided for analysis.", True)
        return None
        
    if not job_description or len(job_description.strip()) < 50:
        error_tracker.add_error("parse_error", "Job description is too short for meaningful analysis.", False)
        job_description += "\n\nThis is a professional position requiring technical skills and relevant experience."

    # Convert resume data to a JSON string for the prompt
    try:
        resume_json_string = json.dumps(resume_data, indent=2)
    except Exception as e:
        error_tracker.add_error("json_error", "Error converting resume data to JSON", True, str(e))
        return None

    prompt = f"""
    You are an expert job application consultant. Based on the job description below and the provided resume data, 
    analyse how well the candidate matches the job requirements and provide constructive feedback.

    Job Description:
    ---
    {job_description}
    ---

    Resume Data (JSON):
    ---
    {resume_json_string}
    ---

    Perform a thorough analysis of the match between this candidate and the job description, including:
    1. An overall "match_score" from 0 to 100, representing their fit for the position.
    2. Three to five key "strengths" that make them a good fit for this specific role.
    3. Three to five main "improvement_areas" where they could enhance their candidacy.
    4. A "skills_assessment" object with ratings (0-100) for these specific categories:
       - "Technical Skills" (relevance to the role)
       - "Experience" (years and quality related to the role)
       - "Education" (relevance and level)
       - "Resume Quality" (clarity, formatting, and presentation)
    5. "recommendations" - practical, specific suggestions to improve their resume and application for this role.
    6. "keyword_analysis" - identify key terms from the job description missing from their resume.
    7. "industry_fit" - assessment of how well the candidate matches the industry requirements for this role.
    8. "potential_job_titles" - alternate job titles that this resume would be well-suited for.
    9. "experience_gap_analysis" - identify specific experience gaps between the resume and job requirements.

    Structure your response as a single, valid JSON object containing these keys.
    Be constructive, honest but encouraging, highlighting both positives and areas for improvement.
    """

    # Use enhanced API call with timeout
    success, response_text = call_anthropic_api_with_timeout(
        client=client,
        prompt=prompt,
        max_tokens=2500,
        temperature=0.1,
        system="You are a professional job application consultant providing detailed, honest but constructive feedback to help job seekers improve their applications.",
        timeout=60,  # 60 second timeout
        retries=1    # 1 retry attempt
    )

    if not success:
        error_tracker.add_error("api_error", f"API call failed during resume analysis: {response_text}", True)
        # Return a basic fallback analysis
        return {
            "match_score": 50, 
            "strengths": ["Unable to analyze due to API error"],
            "improvement_areas": ["Unable to analyze due to API error"],
            "skills_assessment": {
                "Technical Skills": 50,
                "Experience": 50,
                "Education": 50,
                "Resume Quality": 50
            },
            "recommendations": ["Please try again later or contact support."],
            "keyword_analysis": ["Analysis unavailable"],
            "analysis_error": f"API Error: {response_text}"
        }

    # Prepare fallback structure
    fallback_analysis = {
        "match_score": 50, 
        "strengths": ["Data extraction failed - please try again"],
        "improvement_areas": ["Data extraction failed - please try again"],
        "skills_assessment": {
            "Technical Skills": 50,
            "Experience": 50,
            "Education": 50,
            "Resume Quality": 50
        },
        "recommendations": ["Please try again or contact support."],
        "keyword_analysis": ["Analysis unavailable"],
        "industry_fit": "Unknown",
        "potential_job_titles": ["Unable to determine"],
        "experience_gap_analysis": ["Analysis unavailable"],
        "analysis_error": "JSON parsing failed"
    }
    
    # Extract JSON with structured fallbacks
    json_string = extract_json_from_string(response_text, json.dumps(fallback_analysis))
    
    try:
        analysis_data = json.loads(json_string)
        
        # Basic validation
        if not isinstance(analysis_data, dict):
            error_tracker.add_error("json_error", f"Analysis returned {type(analysis_data).__name__} instead of a dictionary.", True)
            return fallback_analysis
            
        # Ensure all required fields exist
        required_fields = [
            "match_score", "strengths", "improvement_areas", 
            "skills_assessment", "recommendations", "keyword_analysis",
            "industry_fit", "potential_job_titles", "experience_gap_analysis"
        ]
        
        for field in required_fields:
            if field not in analysis_data:
                if field in ["strengths", "improvement_areas", "recommendations", "keyword_analysis", "potential_job_titles", "experience_gap_analysis"]:
                    analysis_data[field] = ["Data missing"]
                elif field == "skills_assessment":
                    analysis_data[field] = {
                        "Technical Skills": 50,
                        "Experience": 50,
                        "Education": 50,
                        "Resume Quality": 50
                    }
                elif field == "match_score":
                    analysis_data[field] = 50
                elif field == "industry_fit":
                    analysis_data[field] = "Unknown"
        
        return analysis_data
        
    except json.JSONDecodeError as json_e:
        error_tracker.add_error("json_error", f"Failed to decode analysis JSON: {json_e}", True)
        return fallback_analysis

def generate_interview_tips(client, resume_data, job_description, analysis):
    """
    Generates personalised interview tips based on resume and job description.
    """
    if not resume_data or not job_description or not analysis:
        return ["Unable to generate interview tips due to missing data."]
    
    # Extract key areas where improvement might be needed
    improvement_areas = analysis.get('improvement_areas', [])
    strengths = analysis.get('strengths', [])
    match_score = analysis.get('match_score', 50)
    
    # Convert data to JSON for the prompt
    try:
        resume_json = json.dumps(resume_data, indent=2)
        analysis_json = json.dumps(analysis, indent=2)
    except Exception as e:
        error_tracker.add_error("json_error", f"Error preparing data for interview tips: {e}", False)
        return ["Error generating interview tips."]
    
    prompt = f"""
    You are an expert career coach. Based on this candidate's resume and job description analysis, 
    provide 5 strategic interview preparation tips tailored specifically to them.

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

    Provide 5 specific, actionable interview tips that will help this candidate:
    1. Emphasise their relevant strengths for this position
    2. Address potential concerns about improvement areas
    3. Prepare for likely questions based on the gap between their profile and job requirements
    4. Highlight their unique value proposition for this role
    5. Showcase their enthusiasm and fit for the company/role

    Format each tip with a clear heading and explanation. Be specific, practical and constructive.
    Tailor these tips precisely to this candidate and this job - avoid generic advice.
    """

    # Use enhanced API call with timeout
    success, response_text = call_anthropic_api_with_timeout(
        client=client,
        prompt=prompt,
        max_tokens=1500,
        temperature=0.2,
        system="You are a supportive career coach providing practical, personalized interview advice.",
        timeout=30,
        retries=1
    )
    
    if not success:
        return ["Unable to generate interview tips. Please try again later."]
    
    # Just return the text directly as it's already formatted
    return response_text
