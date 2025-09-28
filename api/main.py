#!/usr/bin/env python3
"""
Simple FastAPI application for AI Product Listing Assistant
Minimal version for Vercel deployment testing
"""

import os
from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="AI Product Listing Assistant API",
    description="API for generating product listings using AI",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific domains
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    """Root endpoint for health check"""
    return {
        "message": "AI Product Listing Assistant API",
        "status": "running",
        "version": "1.0.0",
        "environment": "production"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "ok",
        "message": "API is running",
        "environment": os.environ.get("VERCEL_ENV", "unknown")
    }

@app.post("/generate-product-info")
async def generate_product_info(
    file: UploadFile = File(...),
    language: str = Form(default="English")
):
    """Generate product information from uploaded image"""
    
    try:
        logger.info(f"📸 Processing image: {file.filename}, Language: {language}")
        
        # Validate file type
        if not file.content_type or not file.content_type.startswith('image/'):
            raise HTTPException(
                status_code=400,
                detail="Invalid file type. Please upload an image file."
            )
        
        # Read image data
        image_data = await file.read()
        
        if len(image_data) == 0:
            raise HTTPException(
                status_code=400,
                detail="Empty file uploaded. Please select a valid image."
            )
        
        # For now, return a mock response since the AI service is not available
        # This will be replaced with actual AI analysis once the service is working
        result = {
            "title": f"Sample Product Title ({language})",
            "description": f"This is a sample product description generated for testing purposes. The image was successfully received ({len(image_data)} bytes) and would be analyzed by the AI service in a production environment.",
            "tags": ["sample", "test", "product", language.lower()],
            "language": language,
            "status": "success",
            "note": "This is a test response. AI analysis service is being configured."
        }
        
        logger.info("✅ Mock product analysis completed successfully")
        return JSONResponse(content=result)
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"❌ Error processing request: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
