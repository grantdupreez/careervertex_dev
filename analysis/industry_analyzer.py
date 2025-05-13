import json
from utils.error_tracker import error_tracker
from utils.api_client import call_anthropic_api_with_timeout
from utils.json_parser import extract_json_from_string

def analyze_industry_fit(client, resume_data, job_description, analysis):
    """
    Analyzes how well the candidate fits within the specific industry context.
    """
    if not resume_data or not job_description or not analysis:
        return None
    
    # Convert data to JSON for the prompt
    try:
        resume_json = json.dumps(resume_data, indent=2)
        analysis_json = json.dumps(analysis, indent=2)
    except Exception as e:
        error_tracker.add_error("json_error", f"Error preparing data for industry analysis: {e}", False)
        return None
    
    prompt = f"""
    You are an expert industry analyst specializing in career placement. Based on this candidate's resume, 
    the job description, and previous analysis, provide an industry-specific assessment.

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

    Provide a JSON response with the following structure:
    1. "industry_identified": the specific industry this job is in
    2. "industry_fit_score": numeric score from 0-100 on industry fit
    3. "industry_trends": array of current trends in this industry relevant to the role
    4. "industry_keywords": array of industry-specific keywords that would strengthen the resume
    5. "competitors": array of top companies in this space the candidate should research
    6. "industry_challenges": array of current challenges in this industry the candidate should be aware of
    7. "salary_range": object with "min" and "max" fields showing typical salary range for this role in this industry
    
    Structure your response as a single, valid JSON object containing these keys.
    """

    # Use enhanced API call with timeout
    success, response_text = call_anthropic_api_with_timeout(
        client=client,
        prompt=prompt,
        max_tokens=1500,
        temperature=0.1,
        system="You are an expert industry analyst providing accurate industry insights for job seekers.",
        timeout=30,
        retries=1
    )
    
    if not success:
        return None
    
    # Prepare fallback structure
    fallback_industry = {
        "industry_identified": "Unknown",
        "industry_fit_score": 50,
        "industry_trends": ["Unable to analyze industry trends"],
        "industry_keywords": ["Unable to identify industry keywords"],
        "competitors": ["Unable to identify competitors"],
        "industry_challenges": ["Unable to identify industry challenges"],
        "salary_range": {"min": 0, "max": 0}
    }
    
    # Extract JSON with structured fallbacks
    json_string = extract_json_from_string(response_text, json.dumps(fallback_industry))
    
    try:
        return json.loads(json_string)
    except json.JSONDecodeError:
        error_tracker.add_error("json_error", "Failed to decode industry analysis JSON", False)
        return fallback_industry
