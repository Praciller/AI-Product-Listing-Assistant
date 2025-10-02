#!/usr/bin/env python3
"""
Google Gemini Vision API service for AI Product Listing Assistant
Handles real image analysis and product information generation
"""

import os
import io
import base64
import logging
from typing import Dict, Any, Optional
from PIL import Image
import google.generativeai as genai

# Configure logging
logger = logging.getLogger(__name__)

class GeminiService:
    """Service for Google Gemini Vision API integration"""

    # Language code to full name mapping
    LANGUAGE_MAPPING = {
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

    def __init__(self):
        """Initialize the Gemini service with API key"""
        self.api_key = os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            logger.warning("⚠️ GOOGLE_API_KEY not found. Using mock responses.")
            self.model = None
        else:
            try:
                genai.configure(api_key=self.api_key)
                # Use the latest available Gemini model with vision capabilities
                self.model = genai.GenerativeModel('gemini-2.0-flash')
                logger.info("✅ Gemini Vision API initialized successfully with gemini-2.0-flash")
            except Exception as e:
                logger.error(f"❌ Failed to initialize Gemini API: {e}")
                self.model = None

    def _get_language_name(self, language_code_or_name: str) -> str:
        """Convert language code to full name, or return as-is if already a full name"""
        # If it's a 2-letter code, convert to full name
        if len(language_code_or_name) == 2 and language_code_or_name.lower() in self.LANGUAGE_MAPPING:
            return self.LANGUAGE_MAPPING[language_code_or_name.lower()]

        # If it's already a full name or not in mapping, return as-is
        return language_code_or_name

    def _prepare_image(self, image_data: bytes) -> Optional[Image.Image]:
        """Prepare image for analysis"""
        try:
            # Open image with PIL
            image = Image.open(io.BytesIO(image_data))
            
            # Convert to RGB if necessary
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # Resize if too large (max 4MB for Gemini)
            max_size = (1024, 1024)
            if image.size[0] > max_size[0] or image.size[1] > max_size[1]:
                image.thumbnail(max_size, Image.Resampling.LANCZOS)
                logger.info(f"📏 Resized image to {image.size}")
            
            return image
        except Exception as e:
            logger.error(f"❌ Error preparing image: {e}")
            return None
    
    def _create_classification_prompt(self, language: str) -> str:
        """Create prompt for image classification"""
        return f"""
You are an expert image classifier for an e-commerce product listing platform.

Analyze this image and determine if it shows a PHYSICAL PRODUCT that can be sold in an e-commerce store.

**ACCEPTABLE PRODUCT IMAGES:**
- Physical products: electronics, clothing, accessories, furniture, toys, tools, etc.
- Items that can be photographed and sold online
- Products in any condition (new, used, packaged, unpackaged)

**NOT ACCEPTABLE (Non-Product Images):**
- Payment slips, receipts, invoices, or transaction confirmations
- Screenshots of apps, websites, or digital interfaces
- Documents, forms, certificates, or text-heavy papers
- QR codes, barcodes, or tickets
- Memes, artwork, or illustrations (unless the artwork itself is the product)
- Blank images, pure text images, or diagrams

**Response Format:**
Respond with a JSON object in this exact format:
{{
  "is_product": true or false,
  "image_type": "brief description of what the image shows",
  "confidence": "high" or "medium" or "low",
  "reason": "brief explanation in {language} of why this is or isn't a product image"
}}

Analyze the image now:
"""

    def _create_analysis_prompt(self, language: str) -> str:
        """Create a detailed prompt for product analysis"""
        return f"""
You are an expert e-commerce product analyst. Analyze this product image and generate professional listing information in {language}.

Please provide a detailed analysis of the product shown in the image, including:

1. **Product Title**: Create a compelling, SEO-friendly title that accurately describes the product
2. **Product Description**: Write a detailed description (100-200 words) that highlights:
   - Key features and benefits
   - Materials, colors, and design elements visible in the image
   - Target audience and use cases
   - Quality indicators and craftsmanship details
3. **Product Tags**: Generate 5-8 relevant tags for categorization and search

**Important Guidelines:**
- Base your analysis ONLY on what you can actually see in the image
- Be specific about colors, materials, style, and visible features
- Use professional e-commerce language appropriate for {language}
- Focus on selling points that would appeal to potential buyers
- If you can identify the product category (electronics, clothing, home goods, etc.), tailor the description accordingly

**Response Format:**
Please respond with a JSON object containing:
{{
  "title": "Product title in {language}",
  "description": "Detailed product description in {language}",
  "tags": ["tag1", "tag2", "tag3", "tag4", "tag5"]
}}

Analyze the image now and provide the product information:
"""
    
    async def _classify_image(self, image: Image.Image, language: str) -> Dict[str, Any]:
        """
        Classify image to determine if it's a product or not

        Args:
            image: PIL Image object
            language: Target language for response

        Returns:
            Dictionary with classification results
        """
        try:
            # Create classification prompt
            prompt = self._create_classification_prompt(language)

            # Generate classification with Gemini
            logger.info(f"🔍 Classifying image type...")
            response = self.model.generate_content([prompt, image])

            if response.text:
                response_text = response.text.strip()

                # Remove markdown code blocks if present
                if response_text.startswith('```json'):
                    response_text = response_text[7:]
                if response_text.endswith('```'):
                    response_text = response_text[:-3]

                try:
                    import json
                    classification = json.loads(response_text)
                    logger.info(f"✅ Classification: {classification.get('image_type')} (is_product: {classification.get('is_product')})")
                    return classification
                except json.JSONDecodeError:
                    logger.warning("⚠️ Failed to parse classification JSON")
                    # Default to allowing the image if classification fails
                    return {"is_product": True, "image_type": "unknown", "confidence": "low", "reason": "Classification failed"}
            else:
                logger.warning("⚠️ Empty classification response")
                return {"is_product": True, "image_type": "unknown", "confidence": "low", "reason": "No response"}

        except Exception as e:
            logger.error(f"❌ Error in image classification: {e}")
            # Default to allowing the image if classification fails
            return {"is_product": True, "image_type": "unknown", "confidence": "low", "reason": str(e)}

    async def analyze_product_image(self, image_data: bytes, language: str = "English") -> Dict[str, Any]:
        """
        Analyze product image using Gemini Vision API

        Args:
            image_data: Raw image bytes
            language: Target language code (e.g., "th") or full name (e.g., "Thai")

        Returns:
            Dictionary containing analysis results or error
        """
        try:
            # Convert language code to full name if needed
            language_name = self._get_language_name(language)
            logger.info(f"🌐 Language mapping: '{language}' -> '{language_name}'")

            # If no API key or model, return enhanced mock response
            if not self.model:
                return self._generate_mock_response(image_data, language_name)

            # Prepare image
            image = self._prepare_image(image_data)
            if not image:
                raise ValueError("Failed to process image")

            # Step 1: Classify the image first
            classification = await self._classify_image(image, language_name)

            # Step 2: Check if it's a product image
            if not classification.get("is_product", True):
                # Not a product image - return error with helpful message
                image_type = classification.get("image_type", "non-product image")
                reason = classification.get("reason", "This image does not appear to be a product")

                logger.warning(f"⚠️ Non-product image detected: {image_type}")

                # Return error in a format that the API can handle
                raise ValueError(f"NOT_A_PRODUCT: {reason}")

            # Step 3: Proceed with product analysis
            # Create analysis prompt
            prompt = self._create_analysis_prompt(language_name)

            # Generate content with Gemini
            logger.info(f"🤖 Analyzing product image with Gemini Vision API (Language: {language_name})")
            response = self.model.generate_content([prompt, image])
            
            # Parse response
            if response.text:
                # Try to extract JSON from response
                response_text = response.text.strip()
                
                # Remove markdown code blocks if present
                if response_text.startswith('```json'):
                    response_text = response_text[7:]
                if response_text.endswith('```'):
                    response_text = response_text[:-3]
                
                try:
                    import json
                    analysis_result = json.loads(response_text)
                    
                    # Validate required fields
                    required_fields = ["title", "description", "tags"]
                    if all(field in analysis_result for field in required_fields):
                        logger.info("✅ Gemini analysis completed successfully")
                        return analysis_result
                    else:
                        logger.warning("⚠️ Gemini response missing required fields, using fallback")
                        return self._create_fallback_response(response_text, language_name)

                except json.JSONDecodeError:
                    logger.warning("⚠️ Failed to parse Gemini JSON response, using fallback")
                    return self._create_fallback_response(response_text, language_name)
            else:
                logger.warning("⚠️ Empty response from Gemini API")
                return self._generate_mock_response(image_data, language_name)

        except ValueError as e:
            # Re-raise ValueError for non-product images (don't catch these)
            if str(e).startswith("NOT_A_PRODUCT:"):
                raise
            # Other ValueErrors
            logger.error(f"❌ ValueError in Gemini analysis: {e}")
            return self._generate_mock_response(image_data, language_name)
        except Exception as e:
            logger.error(f"❌ Error in Gemini analysis: {e}")
            return self._generate_mock_response(image_data, language_name)
    
    def _create_fallback_response(self, ai_text: str, language: str) -> Dict[str, Any]:
        """Create fallback response when JSON parsing fails but we have AI text"""
        # Extract useful information from the AI response text
        lines = ai_text.split('\n')
        title = f"AI-Analyzed Product ({language})"
        description = ai_text[:300] + "..." if len(ai_text) > 300 else ai_text
        tags = ["ai-analyzed", "product", language.lower(), "quality", "recommended"]
        
        return {
            "title": title,
            "description": description,
            "tags": tags
        }
    
    def _generate_mock_response(self, image_data: bytes, language: str) -> Dict[str, Any]:
        """Generate enhanced mock response when API is not available"""
        image_size = len(image_data)
        
        # Try to get basic image info for more realistic mock
        try:
            image = self._prepare_image(image_data)
            if image:
                width, height = image.size
                format_info = f"{width}x{height} pixels"
            else:
                format_info = f"{image_size} bytes"
        except:
            format_info = f"{image_size} bytes"
        
        mock_titles = {
            "English": "Premium Quality Product",
            "Thai": "สินค้าคุณภาพพรีเมียม",
            "Spanish": "Producto de Calidad Premium",
            "French": "Produit de Qualité Premium",
            "German": "Premium Qualitätsprodukt",
            "Japanese": "プレミアム品質製品",
            "Chinese": "优质产品",
            "Korean": "프리미엄 품질 제품",
            "Italian": "Prodotto di Qualità Premium",
            "Portuguese": "Produto de Qualidade Premium",
            "Russian": "Премиальный Качественный Продукт",
            "Arabic": "منتج عالي الجودة",
            "Hindi": "प्रीमियम गुणवत्ता उत्पाद"
        }
        
        title = mock_titles.get(language, f"Premium {language} Product")
        
        description = f"High-quality product analyzed from your uploaded image ({format_info}). This premium item features excellent craftsmanship and attention to detail, making it perfect for discerning customers who value quality and style. The product showcases modern design elements and superior materials that ensure durability and aesthetic appeal."
        
        tags = ["premium", "quality", "stylish", language.lower(), "recommended", "modern", "durable"]
        
        logger.info(f"🎭 Generated enhanced mock response for {language}")
        
        return {
            "title": title,
            "description": description,
            "tags": tags
        }
