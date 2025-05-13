import time
import traceback
import streamlit as st
import anthropic
from utils.error_tracker import error_tracker

#def call_anthropic_api_with_timeout(client, prompt, model="claude-3-5-sonnet-20240620", 
#                                   max_tokens=2000, temperature=0.0, system="", 
#                                   timeout=60, retries=2):
#    """
# try the new model: claude-3-7-sonnet-20250219
def call_anthropic_api_with_timeout(client, prompt, model="claude-3-5-haiku-20241022", 
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
            # Create a timeout context
            response = client.messages.create(
                model=model,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system,
                messages=[{"role": "user", "content": prompt}],
                timeout=timeout  # Will raise exception if call takes too long
            )
            
            if response and hasattr(response, 'content') and len(response.content) > 0:
                return True, response.content[0].text
            else:
                return False, "Empty response received from API"
                
        except anthropic.APITimeoutError:
            if current_attempt <= retries:
                remaining_time = timeout - (time.time() - start_time)
                if remaining_time > 0:
                    st.warning(f"API timeout. Retrying... (Attempt {current_attempt}/{retries})")
                    time.sleep(min(3, remaining_time))  # Brief pause before retry
                else:
                    error_tracker.add_error("api_timeout", f"Timeout after {timeout} seconds. The request took too long to complete.", True)
                    return False, f"Timeout after {timeout} seconds. The request took too long to complete."
            else:
                error_tracker.add_error("api_timeout", f"Request timed out after {timeout} seconds and {retries} retries.", True)
                return False, f"Request timed out after {timeout} seconds and {retries} retries."
        except anthropic.APIConnectionError as e:
            error_tracker.add_error("api_error", "Connection error when calling AI service", True, str(e))
            return False, f"Connection error: {str(e)}"
        except anthropic.APIError as e:
            error_tracker.add_error("api_error", "API error from AI service", True, str(e))
            return False, f"API error: {str(e)}"
        except anthropic.RateLimitError as e:
            error_tracker.add_error("api_error", "Rate limit exceeded when calling AI service", True, str(e))
            return False, f"Rate limit exceeded: {str(e)}"
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            error_tracker.add_error("api_error", "Unexpected error when calling AI service", True, traceback.format_exc())
            return False, error_msg
    
    return False, "Maximum retries exceeded with no successful response."

def initialize_anthropic_client():
    """Initialize the Anthropic client with proper error handling."""
    try:
        # Use anthropic.Anthropic for newer versions
        client = anthropic.Anthropic(api_key=st.secrets["ANTHROPIC_API_KEY"])
        return client
    except AttributeError:
        # Fallback for older versions if needed
        client = anthropic.Client(api_key=st.secrets["ANTHROPIC_API_KEY"])
        return client
    except KeyError:
        st.error("ANTHROPIC_API_KEY not found in Streamlit secrets. Please add it to your .streamlit/secrets.toml file.")
        st.info("To learn how to set up Streamlit secrets, visit: https://docs.streamlit.io/library/advanced-features/secrets-management")
        return None
