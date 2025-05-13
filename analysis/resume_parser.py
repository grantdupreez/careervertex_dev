import json
from functools import lru_cache
from utils.error_tracker import error_tracker
from utils.api_client import call_anthropic_api_with_timeout
from utils.json_parser import extract_json_from_string

@lru_cache(maxsize=10)  # Cache for performance
def parse_resume(client, resume_text, candidate_name):
    """
    Parses a resume and returns a dictionary with structured data.
    Uses caching for performance improvements.
    """
    if not resume_text or len(resume_text.strip()) < 50:
        error_tracker.add_error("parse_error", "Your resume contains too little text to parse effectively.", False)
        # Return fallback structure
        return {
            "name": candidate_name,
            "contact_info": {"email": None, "phone": None},
            "education": [],
            "work_experience": [{"title": "Unknown", "description": "Resume text extraction failed or contained too little text."}],
            "skills": {"technical": [], "soft": []},
            "certifications": [],
            "original_filename": candidate_name,
            "parsing_error": "Text extraction failed or insufficient content"
        }

    prompt = f"""
    Please extract the following information from the resume provided below for candidate '{candidate_name}'.
    Structure the output as a single JSON object containing these keys:
    - "name": (string, if found, otherwise use '{candidate_name}')
    - "contact_info": (object with "email" and "phone" keys, strings, null if not found)
    - "education": (array of strings or objects describing education, empty array if none)
    - "work_experience": (array of strings or objects describing work experience including years/duration, empty array if none)
    - "skills": (object with "technical" and "soft" keys, each containing an array of strings, empty arrays if none)
    - "certifications": (array of strings, empty array if none)
    - "original_filename": (string, always include '{candidate_name}')

    IMPORTANT: Respond ONLY with the valid JSON object. Do not include any introductory text, explanations, or markdown formatting like ```json.

    Resume for candidate {candidate_name}:
    ---
    {resume_text}
    ---
    """

    # Use enhanced API call with timeout
    success, response_text = call_anthropic_api_with_timeout(
        client=client,
        prompt=prompt,
        max_tokens=1500,
        temperature=0.0,
        system="You are an expert resume parser. Extract structured information accurately and return ONLY a valid JSON object as specified.",
        timeout=45,  # 45 second timeout
        retries=1    # 1 retry attempt
    )

    if not success:
        error_tracker.add_error("api_error", f"API call failed during resume parsing: {response_text}", True)
        # Return fallback structure on API failure
        return {
            "name": candidate_name,
            "contact_info": {"email": None, "phone": None},
            "education": [],
            "work_experience": [{"title": "Unknown", "description": "API call failed during resume parsing."}],
            "skills": {"technical": [], "soft": []},
            "certifications": [],
            "original_filename": candidate_name,
            "parsing_error": f"API Error: {response_text}"
        }

    # Prepare fallback structure for JSON parsing failures
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

    # Extract JSON with structured fallbacks
    json_string = extract_json_from_string(response_text, json.dumps(fallback_structure))
    
    try:
        parsed_data = json.loads(json_string)
        
        # Ensure it's a dictionary
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
