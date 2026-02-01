"""
Slide Generator Module - Generates Sequoia-style pitch decks using Manus 1.6 API
"""

import os
import json
import requests
import asyncio
from typing import Optional, Dict, Any
from google import genai
from google.genai import types

# Manus API configuration
MANUS_API_URL = os.environ.get("MANUS_API_URL", "https://api.manus.im/v1")
# Manus API configuration
MANUS_API_URL = os.environ.get("MANUS_API_URL", "https://api.manus.im/v1")
# Key loaded lazily


# Slide structure for Sequoia-style pitch deck
SLIDE_STRUCTURE = [
    {"number": 1, "name": "Title", "fields": ["company-purpose"], "description": "Company name and one-line purpose"},
    {"number": 2, "name": "Purpose", "fields": ["company-purpose"], "description": "What the company exists to do"},
    {"number": 3, "name": "Problem", "fields": ["problem-formula", "problem-breaks", "evidence-market"], "description": "The pain point being solved"},
    {"number": 4, "name": "Solution", "fields": ["product-description", "differentiation"], "description": "How the product solves the problem"},
    {"number": 5, "name": "Why Now", "fields": ["why-now"], "description": "Market timing and inflection points"},
    {"number": 6, "name": "Market Size", "fields": ["tam", "sam", "som", "market-state"], "description": "TAM/SAM/SOM analysis"},
    {"number": 7, "name": "Competition", "fields": ["competitors"], "description": "Competitive landscape and positioning"},
    {"number": 8, "name": "Product", "fields": ["core-capabilities", "moat"], "description": "Core capabilities and competitive moat"},
    {"number": 9, "name": "Business Model", "fields": ["value-customer", "value-current"], "description": "How value is created and captured"},
    {"number": 10, "name": "Team", "fields": ["founder-motivation", "founder-uniqueness"], "description": "Founder background and fit"},
    {"number": 11, "name": "Traction", "fields": [], "description": "Metrics and progress (if available)"},
    {"number": 12, "name": "Ask", "fields": [], "description": "What you're asking for and contact info"},
]


def extract_dashboard_values(modules: Dict[str, Any]) -> Dict[str, str]:
    """
    Extract all question values from dashboard modules into a flat dictionary.
    """
    values = {}
    
    for module_id, module in modules.items():
        if "subsections" not in module:
            continue
        for subsection in module["subsections"]:
            if "questions" not in subsection:
                continue
            for question in subsection["questions"]:
                question_id = question.get("id", "")
                question_value = question.get("value", "")
                if question_id and question_value:
                    values[question_id] = question_value
    
    return values


def generate_fallback_content(idea: str, field_name: str, gemini_client) -> str:
    """
    Use Gemini to generate content for a missing field based on the initial idea.
    """
    prompt = f"""
    Based on this startup idea: "{idea}"
    
    Generate content for the field: {field_name}
    
    Keep the response concise (2-3 sentences max) and professional.
    Return only the content, no explanations.
    """
    
    try:
        response = gemini_client.models.generate_content(
            model='gemini-2.0-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.7,
                max_output_tokens=200
            )
        )
        return response.text.strip()
    except Exception as e:
        print(f"Fallback generation error for {field_name}: {e}")
        return ""


def prepare_slide_data(
    modules: Dict[str, Any], 
    idea: str,
    gemini_client
) -> Dict[str, Any]:
    """
    Prepare slide data by extracting dashboard values and filling gaps with AI.
    """
    values = extract_dashboard_values(modules)
    slide_data = {}
    
    for slide in SLIDE_STRUCTURE:
        slide_content = {
            "name": slide["name"],
            "description": slide["description"],
            "data": {}
        }
        
        for field in slide["fields"]:
            if field in values and values[field]:
                slide_content["data"][field] = values[field]
            elif idea:
                # Generate fallback content
                fallback = generate_fallback_content(idea, field, gemini_client)
                if fallback:
                    slide_content["data"][field] = f"[AI Generated] {fallback}"
        
        slide_data[f"slide_{slide['number']}"] = slide_content
    
    return slide_data


def generate_manus_prompt(slide_data: Dict[str, Any], idea: str) -> str:
    """
    Generate the prompt for Manus 1.6 to create the pitch deck.
    """
    prompt = f"""
Create a professional 12-slide Sequoia Capital-style pitch deck for a startup.

## Startup Idea
{idea}

## Slide Data
{json.dumps(slide_data, indent=2)}

## Instructions
1. Create a visually stunning, investor-ready pitch deck
2. Use Nano Banana Pro to generate professional visuals for each slide
3. Follow Sequoia's clean, minimal, data-driven aesthetic
4. Each slide should have:
   - Clear title
   - 3-5 bullet points maximum
   - Professional visual/infographic
   - Speaker notes
5. Color scheme: Professional blues, grays, white background
6. Typography: Clean sans-serif, high contrast
7. Export as downloadable PowerPoint (.pptx) format

## Slide Structure
1. Title Slide - Company name and one-liner
2. Purpose - Why we exist
3. Problem - The pain point (with data)
4. Solution - How we solve it
5. Why Now - Market timing
6. Market Size - TAM/SAM/SOM with concentric circles visual
7. Competition - 2x2 positioning matrix
8. Product - Core capabilities
9. Business Model - Value creation
10. Team - Founder credentials
11. Traction - Metrics (or vision if early stage)
12. Ask - Call to action

Generate the complete pitch deck now.
"""
    return prompt


async def generate_pitch_deck_with_manus(
    modules: Dict[str, Any],
    idea: str,
    gemini_client,
    slide_data: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Generate a pitch deck using Manus 1.6 API with Nano Banana Pro.
    
    Returns dict with task_id for polling or direct result.
    """
    # Prepare slide data checking...
    if not slide_data:
        slide_data = prepare_slide_data(modules, idea, gemini_client)
    
    # Generate Manus prompt
    prompt = generate_manus_prompt(slide_data, idea)
    
    # Lazy load API key
    manus_api_key = os.environ.get("MANUS_API_KEY", "")

    # Check if Manus API key is available
    if not manus_api_key:
        # Fallback: Use Gemini to generate slide content as JSON
        return await generate_slides_with_gemini(slide_data, idea, gemini_client)
    
    # Call Manus API
    try:
        print(f"Calling Manus API at {MANUS_API_URL}/tasks")
        print(f"Using API Key: {manus_api_key[:5]}...{manus_api_key[-5:] if manus_api_key else 'None'}")
        
        headers = {
            "Authorization": f"Bearer {manus_api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "prompt": prompt,
            "tools": ["nano_banana_pro"],
            "output_format": "pptx"
        }
        
        response = requests.post(
            f"{MANUS_API_URL}/tasks",
            headers=headers,
            json=payload,
            timeout=120
        )
        
        print(f"Manus Response Status: {response.status_code}")
        
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Manus API error: {response.status_code} - {response.text}")
            # Fallback to Gemini
            return await generate_slides_with_gemini(slide_data, idea, gemini_client)
            
    except Exception as e:
        print(f"Manus API Exception: {e}")
        # Fallback to Gemini
        return await generate_slides_with_gemini(slide_data, idea, gemini_client)


async def generate_slides_with_gemini(
    slide_data: Dict[str, Any],
    idea: str,
    gemini_client
) -> Dict[str, Any]:
    """
    Fallback: Generate slide content using Gemini when Manus is unavailable.
    Returns structured JSON that frontend can render.
    """
    prompt = f"""
Generate a 12-slide Sequoia-style pitch deck as JSON.

Startup Idea: {idea}

Available Data: {json.dumps(slide_data, indent=2)}

Return JSON in this exact format:
{{
    "slides": [
        {{
            "number": 1,
            "title": "Slide title",
            "content": ["bullet 1", "bullet 2", "bullet 3"],
            "visual_description": "Description of the visual for this slide",
            "speaker_notes": "Notes for the presenter"
        }}
    ],
    "metadata": {{
        "company_name": "Extracted or generated company name",
        "tagline": "One-line description"
    }}
}}

Generate all 12 slides following Sequoia's style:
1. Title, 2. Purpose, 3. Problem, 4. Solution, 5. Why Now, 
6. Market Size, 7. Competition, 8. Product, 9. Business Model, 
10. Team, 11. Traction, 12. Ask
"""
    
    try:
        response = await asyncio.to_thread(
            gemini_client.models.generate_content,
            model='gemini-2.0-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.7
            )
        )
        
        result = json.loads(response.text)
        return {
            "status": "completed",
            "type": "json",
            "data": result
        }
        
    except Exception as e:
        print(f"Gemini slide generation error: {e}")
        return {
            "status": "failed",
            "error": str(e)
        }
