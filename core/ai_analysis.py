import streamlit as st
import anthropic
import json
import re

class AIAnalyzer:
    """AI-powered CV and job analysis."""
    
    def __init__(self):
        self.client = self._init_client()
    
    def _init_client(self):
        """Initialize Anthropic client."""
        try:
            return anthropic.Anthropic(api_key=st.secrets["ANTHROPIC_API_KEY"])
        except:
            st.error("Failed to initialize AI client")
            return None
    
    def _clean_json_response(self, response):
        """Extract JSON from AI response."""
        # Try to find JSON in the response
        json_match = re.search(r'\{.*\}', response, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group())
            except:
                pass
        return {}
    
    def parse_cv(self, cv_text, cv_name):
        """Parse CV to extract structured information."""
        if not self.client:
            return {}
        
        prompt = f"""
        Extract the following information from this CV and return ONLY a JSON object:
        - name: candidate's full name
        - email: email address
        - phone: phone number
        - summary: brief professional summary
        - skills: list of key skills
        - experience: list of work experiences with title, company, duration
        - education: list of education entries
        - keywords: important keywords for job matching
        
        CV Text:
        {cv_text}
        
        Return ONLY the JSON object, no other text.
        """
        
        try:
            response = self.client.messages.create(
                model="claude-3-5-sonnet-20240620",
                max_tokens=1500,
                temperature=0,
                messages=[{"role": "user", "content": prompt}]
            )
            
            return self._clean_json_response(response.content[0].text)
        except Exception as e:
            print(f"CV parsing error: {e}")
            return {}
    
    def parse_job_description(self, job_description):
        """Parse job description to extract key requirements."""
        if not self.client:
            return {}
        
        prompt = f"""
        Extract the following from this job description and return ONLY a JSON object:
        - required_skills: list of required technical skills
        - preferred_skills: list of preferred/nice-to-have skills
        - experience_years: minimum years of experience required
        - education: required education level
        - key_responsibilities: main job responsibilities
        - keywords: important keywords and phrases
        
        Job Description:
        {job_description}
        
        Return ONLY the JSON object, no other text.
        """
        
        try:
            response = self.client.messages.create(
                model="claude-3-5-sonnet-20240620",
                max_tokens=1500,
                temperature=0,
                messages=[{"role": "user", "content": prompt}]
            )
            
            return self._clean_json_response(response.content[0].text)
        except Exception as e:
            print(f"Job parsing error: {e}")
            return {}
    
    def analyze_cv_match(self, parsed_cv, job_description, parsed_job):
        """Analyze how well CV matches job description."""
        if not self.client:
            return {}
        
        prompt = f"""
        Analyze how well this candidate matches the job requirements.
        
        Candidate Profile:
        {json.dumps(parsed_cv, indent=2)}
        
        Job Requirements:
        {json.dumps(parsed_job, indent=2)}
        
        Full Job Description:
        {job_description}
        
        Provide a detailed analysis with:
        1. match_score: overall match percentage (0-100)
        2. strengths: list of candidate's strengths for this role
        3. gaps: areas where candidate doesn't meet requirements
        4. suggestions: specific improvements for the CV
        5. missing_keywords: important keywords missing from CV
        6. interview_tips: specific tips for this role
        
        Return ONLY a JSON object with these fields.
        """
        
        try:
            response = self.client.messages.create(
                model="claude-3-5-sonnet-20240620",
                max_tokens=2500,
                temperature=0.1,
                messages=[{"role": "user", "content": prompt}]
            )
            
            return self._clean_json_response(response.content[0].text)
        except Exception as e:
            print(f"Analysis error: {e}")
            return {
                "match_score": 0,
                "strengths": ["Analysis failed"],
                "gaps": ["Please try again"],
                "suggestions": ["Unable to analyze at this time"],
                "missing_keywords": [],
                "interview_tips": []
            }
    
    def generate_cover_letter(self, parsed_cv, job_description, analysis_result):
        """Generate a tailored cover letter."""
        if not self.client:
            return ""
        
        prompt = f"""
        Write a professional cover letter for this candidate applying to this position.
        
        Candidate Profile:
        {json.dumps(parsed_cv, indent=2)}
        
        Job Description:
        {job_description}
        
        Match Analysis:
        {json.dumps(analysis_result, indent=2)}
        
        Create a compelling cover letter that:
        - Highlights relevant experience and skills
        - Addresses the key requirements
        - Shows enthusiasm for the role
        - Uses a professional tone
        - Is concise (300-400 words)
        
        Return ONLY the cover letter text, no other commentary.
        """
        
        try:
            response = self.client.messages.create(
                model="claude-3-5-sonnet-20240620",
                max_tokens=1500,
                temperature=0.3,
                messages=[{"role": "user", "content": prompt}]
            )
            
            return response.content[0].text
        except Exception as e:
            print(f"Cover letter generation error: {e}")
            return "Failed to generate cover letter. Please try again."
    
    def update_cv_suggestions(self, parsed_cv, analysis_result):
        """Generate specific CV update suggestions."""
        if not self.client:
            return []
        
        prompt = f"""
        Based on this CV analysis, provide specific, actionable suggestions to improve the CV.
        
        Current CV:
        {json.dumps(parsed_cv, indent=2)}
        
        Analysis Results:
        {json.dumps(analysis_result, indent=2)}
        
        Provide 5-7 specific suggestions such as:
        - Exact phrases or keywords to add
        - Skills to highlight more prominently
        - Experience descriptions to enhance
        - Formatting improvements
        
        Return ONLY a JSON array of suggestion strings.
        """
        
        try:
            response = self.client.messages.create(
                model="claude-3-5-sonnet-20240620",
                max_tokens=1000,
                temperature=0.1,
                messages=[{"role": "user", "content": prompt}]
            )
            
            # Extract array from response
            text = response.content[0].text
            array_match = re.search(r'\[.*\]', text, re.DOTALL)
            if array_match:
                return json.loads(array_match.group())
            return []
        except Exception as e:
            print(f"Suggestions generation error: {e}")
            return []
