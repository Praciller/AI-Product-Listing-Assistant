"""
Gemini AI Service Layer - Handles basic REST requests and responses to Google Gemini AI.

This service layer provides direct interaction with the Google Gemini AI API
for image analysis and content generation.
"""

import json
import io
from typing import Dict, Any
from PIL import Image
import google.generativeai as genai
import structlog

logger = structlog.get_logger(__name__)


class GeminiService:
    """Service layer for Google Gemini AI interactions."""
    
    def __init__(self, api_key: str):
        """Initialize the Gemini service with API key."""
        self.api_key = api_key
        self._configure_gemini()
        
    def _configure_gemini(self) -> None:
        """Configure Gemini AI with the provided API key."""
        try:
            genai.configure(api_key=self.api_key)
            logger.info("Gemini AI configured successfully")
        except Exception as e:
            logger.error("Failed to configure Gemini AI", error=str(e))
            raise
    
    def analyze_product_image(
        self, 
        image_data: bytes, 
        language: str = "en"
    ) -> Dict[str, Any]:
        """
        Analyze a product image using Gemini AI.
        
        Args:
            image_data: Raw image bytes
            language: Target language for content generation
            
        Returns:
            Dictionary containing title, description, and tags
            
        Raises:
            ValueError: If image is invalid or response parsing fails
            Exception: For other API-related errors
        """
        try:
            # Validate and process image
            image = self._process_image(image_data)
            
            # Generate prompt for the specified language
            prompt = self._create_prompt(language)
            
            # Initialize model and generate content
            model = genai.GenerativeModel('gemini-2.0-flash-exp')
            response = model.generate_content([prompt, image])
            
            # Parse and validate response
            result = self._parse_response(response.text)
            
            logger.info(
                "Successfully analyzed product image",
                language=language,
                title_length=len(result.get('title', '')),
                tags_count=len(result.get('tags', []))
            )
            
            return result
            
        except Exception as e:
            logger.error(
                "Failed to analyze product image",
                error=str(e),
                language=language
            )
            raise
    
    def _process_image(self, image_data: bytes) -> Image.Image:
        """Process and validate image data."""
        try:
            image = Image.open(io.BytesIO(image_data))
            image.verify()  # Verify it's a valid image
            
            # Reset stream for actual use
            image = Image.open(io.BytesIO(image_data))
            return image
            
        except Exception as e:
            raise ValueError(f"Invalid image file: {str(e)}")
    
    def _create_prompt(self, language: str) -> str:
        """Create a language-specific prompt for Gemini AI."""
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
        
        return f"""
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
    
    def _parse_response(self, response_text: str) -> Dict[str, Any]:
        """Parse and validate Gemini AI response."""
        try:
            # Clean the response text (remove markdown formatting if present)
            cleaned_text = response_text.strip()
            if cleaned_text.startswith("```json"):
                cleaned_text = cleaned_text[7:]
            if cleaned_text.endswith("```"):
                cleaned_text = cleaned_text[:-3]
            
            result = json.loads(cleaned_text.strip())
            
            # Validate required keys
            required_keys = ['title', 'description', 'tags']
            if not all(key in result for key in required_keys):
                missing_keys = [key for key in required_keys if key not in result]
                raise ValueError(f"Missing required keys in response: {missing_keys}")
            
            # Validate data types
            if not isinstance(result['tags'], list):
                raise ValueError("Tags must be a list")
            
            if not isinstance(result['title'], str) or not isinstance(result['description'], str):
                raise ValueError("Title and description must be strings")
            
            return result
            
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse AI response as JSON: {str(e)}")
        except Exception as e:
            raise ValueError(f"Invalid AI response format: {str(e)}")
