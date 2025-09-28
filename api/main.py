#!/usr/bin/env python3
"""
AI Product Listing Assistant API with Google Gemini Vision integration
Real AI-powered product image analysis for e-commerce listings
"""

import os
from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging
from dotenv import load_dotenv
from gemini_service import GeminiService

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Gemini service
gemini_service = GeminiService()

app = FastAPI(
    title="AI Product Listing Assistant API",
    description="API for generating product listings using Google Gemini AI",
    version="2.0.0"
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
        "version": "2.0.0",
        "environment": "production",
        "ai_service": "Google Gemini Vision API",
        "features": ["real_image_analysis", "multi_language_support", "accurate_product_listings"]
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
        
        # Analyze image using Google Gemini Vision API
        logger.info(f"🤖 Starting AI analysis for {file.filename} ({len(image_data)} bytes)")
        analysis_data = await gemini_service.analyze_product_image(image_data, language)

        # Return response in the format expected by the frontend
        result = {
            "success": True,
            "data": analysis_data
        }

        logger.info("✅ AI product analysis completed successfully")
        return JSONResponse(content=result)
        
    except HTTPException as e:
        # Return HTTP exceptions in the format expected by the frontend
        error_response = {
            "success": False,
            "error": e.detail
        }
        return JSONResponse(content=error_response, status_code=e.status_code)
    except Exception as e:
        logger.error(f"❌ Error processing request: {str(e)}")
        # Return error in the format expected by the frontend
        error_response = {
            "success": False,
            "error": f"Analysis failed: {str(e)}"
        }
        return JSONResponse(content=error_response, status_code=500)

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
