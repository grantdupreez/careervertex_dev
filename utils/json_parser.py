import json
import re
import streamlit as st
from utils.error_tracker import error_tracker

def extract_json_from_string(text, default_structure=None):
    """
    Extracts JSON object from a string with multiple fallback strategies.
    Returns extracted JSON string or default_structure if all extraction methods fail.
    """
    if not text:
        error_tracker.add_error("parse_error", "Empty response received from API.", True)
        return default_structure
    
    # Strategy 1: Look for JSON within ```json ... ``` markdown fences
    json_pattern = r'```(?:json)?\s*(\{.*\}|\[.*\])\s*```'
    match = re.search(json_pattern, text, re.DOTALL | re.IGNORECASE)
    if match:
        potential_json = match.group(1).strip()
        try:
            # Validate by parsing and re-stringifying to ensure valid JSON
            parsed = json.loads(potential_json)
            return json.dumps(parsed)  # Return validated and normalized JSON string
        except json.JSONDecodeError:
            # If parsing fails, continue to next strategy
            pass
    
    # Strategy 2: Find outermost matching braces/brackets - more careful approach
    # First check if entire text is valid JSON
    try:
        parsed = json.loads(text.strip())
        return json.dumps(parsed)  # Return validated JSON
    except json.JSONDecodeError:
        pass
        
    # Strategy 3: Find the first occurrence of what looks like a JSON object/array
    # This is riskier, so we do it later
    bracket_pattern = r'(\{.*\}|\[.*\])'
    match = re.search(bracket_pattern, text, re.DOTALL)
    if match:
        potential_json = match.group(0).strip()
        try:
            parsed = json.loads(potential_json)
            return json.dumps(parsed)  # Return validated JSON
        except json.JSONDecodeError:
            pass
    
    # Strategy 4: As a last resort, try to clean up the text by removing common issues
    cleaned_text = text.strip()
    # Try to find the first { or [ and the last } or ]
    start_brace = cleaned_text.find('{')
    start_bracket = cleaned_text.find('[')
    end_brace = cleaned_text.rfind('}')
    end_bracket = cleaned_text.rfind(']')
    
    # Determine which kind of structure we're dealing with (if any)
    if start_brace >= 0 and end_brace >= 0 and (start_bracket < 0 or start_brace < start_bracket):
        potential_json = cleaned_text[start_brace:end_brace+1]
    elif start_bracket >= 0 and end_bracket >= 0:
        potential_json = cleaned_text[start_bracket:end_bracket+1]
    else:
        # No valid JSON structure found
        error_tracker.add_error("json_error", "Could not find a valid JSON structure in the response.", True)
        if default_structure is not None:
            st.info("Using fallback structure instead.")
        return default_structure
    
    try:
        parsed = json.loads(potential_json)
        return json.dumps(parsed)  # Return validated JSON
    except json.JSONDecodeError:
        # All strategies failed
        error_tracker.add_error("json_error", "All JSON extraction strategies failed. The response is not valid JSON.", True)
        if default_structure is not None:
            st.info("Using fallback structure instead.")
        return default_structure
