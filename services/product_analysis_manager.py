"""
Product Analysis Manager Layer - Adds abstraction for ease of configuration and testing.

This manager layer provides a higher-level interface for product analysis operations,
handling configuration, validation, and coordination between different services.
"""

import os
from typing import Dict, Any, Optional
from services.gemini_service import GeminiService
import structlog

logger = structlog.get_logger(__name__)


class ProductAnalysisManager:
    """Manager layer for product analysis operations."""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the product analysis manager.
        
        Args:
            api_key: Google AI API key. If not provided, will try to get from environment.
        """
        self.api_key = api_key or self._get_api_key_from_env()
        self.gemini_service = GeminiService(self.api_key)
        
        logger.info("Product Analysis Manager initialized")
    
    def _get_api_key_from_env(self) -> str:
        """Get API key from environment variables."""
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("GOOGLE_API_KEY environment variable is required")
        return api_key
    
    def analyze_product(
        self,
        image_data: bytes,
        filename: str,
        language: str = "en"
    ) -> Dict[str, Any]:
        """
        Analyze a product image and generate listing information.
        
        Args:
            image_data: Raw image bytes
            filename: Original filename for logging/tracking
            language: Target language for content generation
            
        Returns:
            Dictionary containing analysis results and metadata
        """
        try:
            # Validate inputs
            self._validate_inputs(image_data, filename, language)
            
            # Log analysis start
            logger.info(
                "Starting product analysis",
                filename=filename,
                language=language,
                image_size=len(image_data)
            )
            
            # Perform analysis using Gemini service
            analysis_result = self.gemini_service.analyze_product_image(
                image_data=image_data,
                language=language
            )
            
            # Enhance result with metadata
            enhanced_result = self._enhance_result(
                analysis_result, 
                filename, 
                language
            )
            
            logger.info(
                "Product analysis completed successfully",
                filename=filename,
                language=language,
                title_length=len(enhanced_result['data']['title'])
            )
            
            return enhanced_result
            
        except Exception as e:
            logger.error(
                "Product analysis failed",
                filename=filename,
                language=language,
                error=str(e)
            )
            raise
    
    def _validate_inputs(
        self, 
        image_data: bytes, 
        filename: str, 
        language: str
    ) -> None:
        """Validate input parameters."""
        if not image_data:
            raise ValueError("Image data cannot be empty")
        
        if not filename:
            raise ValueError("Filename cannot be empty")
        
        if not language:
            raise ValueError("Language cannot be empty")
        
        # Validate language code
        supported_languages = {
            "en", "th", "zh", "ja", "ko", "es", 
            "fr", "de", "it", "pt", "ru", "ar"
        }
        
        if language not in supported_languages:
            raise ValueError(
                f"Unsupported language: {language}. "
                f"Supported languages: {', '.join(sorted(supported_languages))}"
            )
        
        # Validate image size (max 10MB)
        max_size = 10 * 1024 * 1024  # 10MB
        if len(image_data) > max_size:
            raise ValueError(f"Image size too large: {len(image_data)} bytes (max: {max_size})")
    
    def _enhance_result(
        self, 
        analysis_result: Dict[str, Any], 
        filename: str, 
        language: str
    ) -> Dict[str, Any]:
        """Enhance analysis result with additional metadata."""
        return {
            "success": True,
            "data": analysis_result,
            "metadata": {
                "filename": filename,
                "language": language,
                "title_length": len(analysis_result.get('title', '')),
                "description_length": len(analysis_result.get('description', '')),
                "tags_count": len(analysis_result.get('tags', []))
            }
        }
    
    def get_supported_languages(self) -> Dict[str, str]:
        """Get list of supported languages."""
        return {
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
    
    def validate_language(self, language: str) -> bool:
        """Check if a language is supported."""
        return language in self.get_supported_languages()
    
    def health_check(self) -> Dict[str, Any]:
        """Perform a health check of the service."""
        try:
            # Check if API key is configured
            if not self.api_key:
                return {
                    "status": "unhealthy",
                    "message": "API key not configured"
                }
            
            # Check if Gemini service is initialized
            if not self.gemini_service:
                return {
                    "status": "unhealthy", 
                    "message": "Gemini service not initialized"
                }
            
            return {
                "status": "healthy",
                "message": "All services operational",
                "supported_languages": len(self.get_supported_languages())
            }
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "message": f"Health check failed: {str(e)}"
            }
