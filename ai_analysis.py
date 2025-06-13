import streamlit as st
import anthropic
import json
import time
import traceback
from utils import extract_json_from_string
from db_manager import log_token_usage

def call_anthropic_api_with_timeout(client, prompt, model="claude-3-5-sonnet-20240620", 
                                   max_tokens=2000, temperature=0.0, system="", 
                                   timeout=60, retries=2):
    """
    Makes an API call to Anthropic with timeout handling and retries.
    """
    start_time = time.time()
    current_attempt = 0
    
    while current_attempt <= retries:
        current_attempt += 1
        try:
            response = client.messages.create(
                model=model,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system,
                messages=[{"role": "user", "content": prompt}],
                timeout=timeout
            )
            
            if response and hasattr(response, 'content') and len(response.content) > 0:
                # Calculate token usage and log it if user_id is available
                if 'user_id' in st.session_state and 'db_manager' in st.session_state:
                    tokens_used = response.usage.input_tokens + response.usage.output_tokens
                    log_token_usage(st.session_state['db_manager'], st.session_state['user_id'], "cv_analysis", tokens_used)
                    
                return True, response.content[0].text
            else:
                return False, "Empty response received from API"
                
        except anthropic.APITimeoutError:
            if current_attempt <= retries:
                remaining_time = timeout - (time.time() - start_time)
                if remaining_time > 0:
                    st.warning(f"API timeout. Retrying... (Attempt {current_attempt}/{retries})")
                    time.sleep(min(3, remaining_time))
                else:
                    return False, f"Timeout after {timeout} seconds. The request took too long to complete."
            else:
                return False, f"Request timed out after {timeout} seconds and {retries} retries."
        except anthropic.APIConnectionError as e:
            return False, f"Connection error: {str(e)}"
        except anthropic.APIError as e:
            return False, f"API error: {str(e)}"
        except anthropic.RateLimitError as e:
            return False, f"Rate limit exceeded: {str(e)}"
        except Exception as e:
            return False, f"Unexpected error: {str(e)}"
    
    return False, "Maximum retries exceeded with no successful response."

def initialize_anthropic_client():
    """Initialize the Anthropic client with proper error handling."""
    try:
        if "ANTHROPIC_API_KEY" not in st.secrets:
            st.error("ANTHROPIC_API_KEY not found in Streamlit secrets.")
            return None
            
        client = anthropic.Anthropic(api_key=st.secrets["ANTHROPIC_API_KEY"])
        return client
    except Exception as e:
        st.error(f"Failed to initialize Anthropic client: {str(e)}")
        return None

def parse_cv(client, cv_text, candidate_name, error_tracker):
    """
    Parses a CV and returns a dictionary with structured data.
    """
    if not cv_text or len(cv_text.strip()) < 50:
        error_tracker.add_error("parse_error", "Your CV contains too little text to parse effectively.", False)
        return {
            "name": candidate_name,
            "contact_info": {"email": None, "phone": None},
            "education": [],
            "work_experience": [{"title": "Unknown", "description": "CV text extraction failed or contained too little text."}],
            "skills": {"technical": [], "soft": []},
            "certifications": [],
            "original_filename": candidate_name,
            "parsing_error": "Text extraction failed or insufficient content"
        }

    prompt = f"""
    Please extract the following information from the CV provided below for candidate '{candidate_name}'.
    Structure the output as a single JSON object containing these keys:
    - "name": (string, if found, otherwise use '{candidate_name}')
    - "contact_info": (object with "email" and "phone" keys, strings, null if not found)
    - "education": (array of strings or objects describing education, empty array if none)
    - "work_experience": (array of strings or objects describing work experience including years/duration, empty array if none)
    - "skills": (object with "technical" and "soft" keys, each containing an array of strings, empty arrays if none)
    - "certifications": (array of strings, empty array if none)
    - "original_filename": (string, always include '{candidate_name}')

    IMPORTANT: Respond ONLY with the valid JSON object. Do not include any introductory text, explanations, or markdown formatting like ```json.

    CV for candidate {candidate_name}:
    ---
    {cv_text}
    ---
    """

    success, response_text = call_anthropic_api_with_timeout(
        client=client,
        prompt=prompt,
        max_tokens=1500,
        temperature=0.0,
        system="You are an expert CV parser. Extract structured information accurately and return ONLY a valid JSON object as specified.",
        timeout=45,
        retries=1
    )

    if not success:
        error_tracker.add_error("api_error", f"API call failed during CV parsing: {response_text}", True)
        return {
            "name": candidate_name,
            "contact_info": {"email": None, "phone": None},
            "education": [],
            "work_experience": [{"title": "Unknown", "description": "API call failed during CV parsing."}],
            "skills": {"technical": [], "soft": []},
            "certifications": [],
            "original_filename": candidate_name,
            "parsing_error": f"API Error: {response_text}"
        }

    fallback_structure = {
        "name": candidate_name,
        "contact_info": {"email": None, "phone": None},
        "education": [],
        "work_experience": [],
        "skills": {"technical": [], "soft": []},
        "certifications": [],
        "original_filename": candidate_name,
        "parsing_error": "JSON parsing failed"
    }

    json_string = extract_json_from_string(response_text, json.dumps(fallback_structure))
    
    try:
        parsed_data = json.loads(json_string)
        
        if not isinstance(parsed_data, dict):
            error_tracker.add_error("json_error", f"Parsing returned {type(parsed_data).__name__} instead of a dictionary.", True)
            return fallback_structure
            
        # Validate and ensure essential fields exist
        if 'original_filename' not in parsed_data:
            parsed_data['original_filename'] = candidate_name
        if 'name' not in parsed_data or not parsed_data['name']:
            parsed_data['name'] = candidate_name
        
        # Ensure proper structure for nested objects
        if 'contact_info' not in parsed_data or not isinstance(parsed_data['contact_info'], dict):
            parsed_data['contact_info'] = {"email": None, "phone": None}
        if 'skills' not in parsed_data or not isinstance(parsed_data['skills'], dict):
            parsed_data['skills'] = {"technical": [], "soft": []}
            
        # Ensure arrays for collections
        for field in ['education', 'work_experience', 'certifications']:
            if field not in parsed_data or not isinstance(parsed_data[field], list):
                parsed_data[field] = []
                
        return parsed_data
        
    except json.JSONDecodeError as json_e:
        error_tracker.add_error("json_error", f"Failed to decode JSON response: {json_e}", True)
        return fallback_structure

def analyze_cv_match(client, cv_data, job_description, error_tracker):
    """
    Analyses how well a CV matches with a job description.
    Returns a match analysis with scores and recommendations.
    """
    if not cv_data or not cv_data.get('parsed_data'):
        error_tracker.add_error("parse_error", "No CV data provided for analysis.", True)
        return None
        
    if not job_description or len(job_description.strip()) < 50:
        error_tracker.add_error("parse_error", "Job description is too short for meaningful analysis.", False)
        job_description += "\n\nThis is a professional position requiring technical skills and relevant experience."

    try:
        cv_json_string = json.dumps(cv_data['parsed_data'], indent=2)
    except Exception as e:
        error_tracker.add_error("json_error", "Error converting CV data to JSON", True, str(e))
        return None

    prompt = f"""
    You are an expert job application consultant. Based on the job description below and the provided CV data, 
    analyse how well the candidate matches the job requirements and provide constructive feedback.

    Job Description:
    ---
    {job_description}
    ---

    CV Data (JSON):
    ---
    {cv_json_string}
    ---

    Perform a thorough analysis of the match between this candidate and the job description, including:
    1. An overall "match_score" from 0 to 100, representing their fit for the position.
    2. Three to five key "strengths" that make them a good fit for this specific role.
    3. Three to five main "improvement_areas" where they could enhance their candidacy.
    4. A "skills_assessment" object with ratings (0-100) for these specific categories:
       - "Technical Skills" (relevance to the role)
       - "Experience" (years and quality related to the role)
       - "Education" (relevance and level)
       - "CV Quality" (clarity, formatting, and presentation)
    5. "recommendations" - practical, specific suggestions to improve their CV and application for this role.
    6. "keyword_analysis" - identify key terms from the job description missing from their CV.
    7. "industry_fit" - assessment of how well the candidate matches the industry requirements for this role.
    8. "potential_job_titles" - alternate job titles that this CV would be well-suited for.
    9. "experience_gap_analysis" - identify specific experience gaps between the CV and job requirements.

    Structure your response as a single, valid JSON object containing these keys.
    Be constructive, honest but encouraging, highlighting both positives and areas for improvement.
    """

    success, response_text = call_anthropic_api_with_timeout(
        client=client,
        prompt=prompt,
        max_tokens=2500,
        temperature=0.1,
        system="You are a professional job application consultant providing detailed, honest but constructive feedback to help job seekers improve their applications.",
        timeout=60,
        retries=1
    )

    if not success:
        error_tracker.add_error("api_error", f"API call failed during CV analysis: {response_text}", True)
        return {
            "match_score": 50, 
            "strengths": ["Unable to analyze due to API error"],
            "improvement_areas": ["Unable to analyze due to API error"],
            "skills_assessment": {
                "Technical Skills": 50,
                "Experience": 50,
                "Education": 50,
                "CV Quality": 50
            },
            "recommendations": ["Please try again later or contact support."],
            "keyword_analysis": ["Analysis unavailable"],
            "analysis_error": f"API Error: {response_text}"
        }

    fallback_analysis = {
        "match_score": 50, 
        "strengths": ["Data extraction failed - please try again"],
        "improvement_areas": ["Data extraction failed - please try again"],
        "skills_assessment": {
            "Technical Skills": 50,
            "Experience": 50,
            "Education": 50,
            "CV Quality": 50
        },
        "recommendations": ["Please try again or contact support."],
        "keyword_analysis": ["Analysis unavailable"],
        "industry_fit": "Unknown",
        "potential_job_titles": ["Unable to determine"],
        "experience_gap_analysis": ["Analysis unavailable"],
        "analysis_error": "JSON parsing failed"
    }
    
    json_string = extract_json_from_string(response_text, json.dumps(fallback_analysis))
    
    try:
        analysis_data = json.loads(json_string)
        
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
                        "CV Quality": 50
                    }
                elif field == "match_score":
                    analysis_data[field] = 50
                elif field == "industry_fit":
                    analysis_data[field] = "Unknown"
        
        return analysis_data
        
    except json.JSONDecodeError as json_e:
        error_tracker.add_error("json_error", f"Failed to decode analysis JSON: {json_e}", True)
        return fallback_analysis

def generate_interview_tips(client, cv_data, job_description, analysis):
    """
    Generates personalised interview tips based on CV and job description.
    """
    if not cv_data or not job_description or not analysis:
        return ["Unable to generate interview tips due to missing data."]
    
    try:
        cv_json = json.dumps(cv_data['parsed_data'], indent=2)
        analysis_json = json.dumps(analysis, indent=2)
    except Exception as e:
        return ["Error generating interview tips."]
    
    prompt = f"""
    You are an expert career coach. Based on this candidate's CV and job description analysis, 
    provide 5 strategic interview preparation tips tailored specifically to them.

    Job Description:
    ---
    {job_description}
    ---

    CV Data:
    ---
    {cv_json}
    ---
    
    CV Analysis:
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
    
    return response_text

def generate_cover_letter(client, cv_data, job_description, analysis):
    """
    Generates a customised cover letter based on CV, job description, and match analysis.
    """
    if not cv_data or not job_description or not analysis:
        return "Unable to generate cover letter due to missing data."
    
    try:
        cv_json = json.dumps(cv_data['parsed_data'], indent=2)
        analysis_json = json.dumps(analysis, indent=2)
    except Exception as e:
        return "Error generating cover letter."
    
    prompt = f"""
    You are an expert career consultant. Based on this candidate's CV and the job description analysis, 
    create a professional cover letter that highlights their relevant qualifications and fit for the role.

    Job Description:
    ---
    {job_description}
    ---

    CV Data:
    ---
    {cv_json}
    ---
    
    CV Analysis:
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
    
    return response_text
