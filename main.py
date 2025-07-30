"""
AI Product Listing Assistant - FastAPI Backend

This application uses Google Gemini AI to analyze product images and generate
optimized e-commerce listings including titles, descriptions, and tags in
multiple languages.

Author: AI Product Listing Assistant
Version: 1.0.0
"""

import os
import json
import io
from typing import Dict, List
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import google.generativeai as genai
from PIL import Image
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Initialize FastAPI application
app = FastAPI(
    title="AI Product Listing Assistant",
    description="Generate AI-powered product listings from images using Google Gemini",
    version="1.0.0"
)

# Add CORS middleware to allow frontend connections
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure Gemini AI
def configure_gemini():
    """Configure Gemini AI with API key from environment variable"""
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("GOOGLE_API_KEY environment variable is required")
    genai.configure(api_key=api_key)

@app.on_event("startup")
async def startup_event():
    """Initialize Gemini AI on startup"""
    try:
        configure_gemini()
        print("✅ Gemini AI configured successfully")
    except Exception as e:
        print(f"⚠️ Warning: Gemini AI configuration failed: {e}")

@app.get("/")
async def root():
    """Health check endpoint"""
    return {"message": "AI Product Listing Assistant API is running!"}

@app.post("/generate-product-info")
async def generate_product_info(
    file: UploadFile = File(...),
    language: str = Form("en")
) -> Dict:
    """
    Analyze a product image and generate title, description, and tags in the specified language
    """
    try:
        # Validate file type
        if not file.content_type.startswith("image/"):
            raise HTTPException(status_code=400, detail="File must be an image")

        # Read image data
        image_data = await file.read()

        # Open image with PIL to validate
        try:
            image = Image.open(io.BytesIO(image_data))
            image.verify()  # Verify it's a valid image
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid image file")

        # Reset image data stream for Gemini
        image = Image.open(io.BytesIO(image_data))

        # Language mapping for better prompts
        language_names = {
            "en": "English",
            "th": "Thai",
            "zh": "Chinese",
            "ja": "Japanese",
            "ko": "Korean",
            "es": "Spanish",
            "fr": "French",
            "de": "German",
            "it": "Italian",
            "pt": "Portuguese",
            "ru": "Russian",
            "ar": "Arabic"
        }

        language_name = language_names.get(language, "English")

        # Create the prompt for Gemini with language specification
        prompt = f"""
        Analyze this product image and act as an expert e-commerce copywriter.
        Generate ALL content in {language_name} language.

        Return a JSON object with exactly three keys:
        - 'title': A catchy, SEO-friendly product name in {language_name} (max 60 characters)
        - 'description': A compelling 2-3 sentence product description in {language_name} highlighting key features and benefits
        - 'tags': A list of exactly 5 relevant keywords/tags in {language_name} for search optimization

        IMPORTANT:
        - ALL text content must be written in {language_name}
        - Use natural, native {language_name} expressions and terminology
        - Make sure the response is valid JSON format only, no additional text
        - Do not mix languages - everything should be in {language_name}
        """

        # Initialize Gemini model
        model = genai.GenerativeModel('gemini-2.0-flash-exp')

        # Generate content with image and prompt
        response = model.generate_content([prompt, image])

        # Parse the response
        try:
            # Clean the response text (remove markdown formatting if present)
            response_text = response.text.strip()
            if response_text.startswith("```json"):
                response_text = response_text[7:]
            if response_text.endswith("```"):
                response_text = response_text[:-3]

            result = json.loads(response_text.strip())

            # Validate the required keys
            required_keys = ['title', 'description', 'tags']
            if not all(key in result for key in required_keys):
                raise ValueError("Missing required keys in response")

            # Ensure tags is a list
            if not isinstance(result['tags'], list):
                raise ValueError("Tags must be a list")

            return {
                "success": True,
                "data": result,
                "filename": file.filename
            }

        except json.JSONDecodeError as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to parse AI response as JSON: {str(e)}"
            )
        except ValueError as e:
            raise HTTPException(
                status_code=500,
                detail=f"Invalid AI response format: {str(e)}"
            )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
