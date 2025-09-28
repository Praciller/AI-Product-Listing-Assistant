"""
AI Product Listing Assistant - FastAPI Backend

This application uses Google Gemini AI to analyze product images and generate
optimized e-commerce listings including titles, descriptions, and tags in
multiple languages.

Features a robust architecture with service/manager/resilience layers for
production-ready reliability and maintainability.

Author: AI Product Listing Assistant
Version: 2.0.0
"""

import os
from typing import Dict
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import structlog

from services.resilient_product_analysis_service import (
    ResilientProductAnalysisService,
    CircuitBreakerError
)

# Load environment variables from .env file
load_dotenv()

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)

# Initialize FastAPI application
app = FastAPI(
    title="AI Product Listing Assistant",
    description="Generate AI-powered product listings from images using Google Gemini with enterprise-grade reliability",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware to allow frontend connections
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize the resilient service
resilient_service = None

@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    global resilient_service

    try:
        resilient_service = ResilientProductAnalysisService()
        logger.info("✅ AI Product Listing Assistant started successfully")
    except Exception as e:
        logger.error("⚠️ Warning: Service initialization failed", error=str(e))

@app.get("/")
async def root():
    """Health check endpoint"""
    return {"message": "AI Product Listing Assistant API is running!"}


@app.get("/health")
async def health_check():
    """Comprehensive health check endpoint"""
    try:
        if not resilient_service:
            return {
                "status": "unhealthy",
                "message": "Service not initialized"
            }

        health_status = resilient_service.health_check()
        return health_status

    except Exception as e:
        logger.error("Health check failed", error=str(e))
        return {
            "status": "unhealthy",
            "message": f"Health check error: {str(e)}"
        }


@app.get("/languages")
async def get_supported_languages():
    """Get list of supported languages"""
    try:
        if not resilient_service:
            raise HTTPException(status_code=503, detail="Service not available")

        languages = resilient_service.get_supported_languages()
        return {
            "success": True,
            "languages": languages,
            "count": len(languages)
        }

    except Exception as e:
        logger.error("Failed to get supported languages", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/circuit-breaker/status")
async def get_circuit_breaker_status():
    """Get circuit breaker status"""
    try:
        if not resilient_service:
            raise HTTPException(status_code=503, detail="Service not available")

        status = resilient_service.get_circuit_breaker_status()
        return {
            "success": True,
            "circuit_breaker": status
        }

    except Exception as e:
        logger.error("Failed to get circuit breaker status", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/circuit-breaker/reset")
async def reset_circuit_breaker():
    """Reset circuit breaker manually"""
    try:
        if not resilient_service:
            raise HTTPException(status_code=503, detail="Service not available")

        resilient_service.reset_circuit_breaker()
        return {
            "success": True,
            "message": "Circuit breaker reset successfully"
        }

    except Exception as e:
        logger.error("Failed to reset circuit breaker", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/generate-product-info")
async def generate_product_info(
    file: UploadFile = File(...),
    language: str = Form("en")
) -> Dict:
    """
    Analyze a product image and generate title, description, and tags in the specified language.

    This endpoint uses a resilient service architecture with retry logic and circuit breaker
    patterns for enterprise-grade reliability.
    """
    try:
        # Validate service availability
        if not resilient_service:
            raise HTTPException(status_code=503, detail="Service not available")

        # Validate file type
        if not file.content_type or not file.content_type.startswith("image/"):
            raise HTTPException(status_code=400, detail="File must be an image")

        # Validate language
        if not resilient_service.validate_language(language):
            supported_languages = list(resilient_service.get_supported_languages().keys())
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported language: {language}. Supported: {', '.join(supported_languages)}"
            )

        # Read image data
        image_data = await file.read()

        if not image_data:
            raise HTTPException(status_code=400, detail="Empty image file")

        # Log request
        logger.info(
            "Processing product analysis request",
            filename=file.filename,
            language=language,
            content_type=file.content_type,
            file_size=len(image_data)
        )

        # Analyze product using resilient service
        try:
            result = resilient_service.analyze_product_with_retry(
                image_data=image_data,
                filename=file.filename or "unknown",
                language=language
            )

            logger.info(
                "Product analysis completed successfully",
                filename=file.filename,
                language=language,
                title_length=len(result.get('data', {}).get('title', ''))
            )

            return result

        except CircuitBreakerError as e:
            logger.warning(
                "Request blocked by circuit breaker",
                filename=file.filename,
                language=language,
                error=str(e)
            )
            raise HTTPException(
                status_code=503,
                detail=f"Service temporarily unavailable: {str(e)}"
            )

    except HTTPException:
        raise
    except Exception as e:
        error_message = str(e)
        logger.error(
            "Unexpected error in product analysis",
            filename=getattr(file, 'filename', 'unknown'),
            language=language,
            error=error_message
        )

        # Handle specific error types with user-friendly messages
        if "quota" in error_message.lower() or "429" in error_message:
            raise HTTPException(
                status_code=429,
                detail="API quota exceeded. Please try again later or upgrade your plan."
            )
        elif "rate limit" in error_message.lower():
            raise HTTPException(
                status_code=429,
                detail="Rate limit exceeded. Please wait a moment and try again."
            )
        else:
            raise HTTPException(
                status_code=500,
                detail=f"Analysis failed: {error_message}"
            )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
