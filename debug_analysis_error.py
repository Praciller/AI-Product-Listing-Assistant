#!/usr/bin/env python3
"""
Debug script to reproduce and analyze the "Analysis failed" error
in the AI Product Listing Assistant production application.
"""

import requests
import json
from io import BytesIO

# Production URLs
FRONTEND_URL = "https://ai-product-listing-assistant.vercel.app"
API_URL = "https://ai-product-listing-api.vercel.app"

def create_test_image():
    """Create a minimal test image (1x1 pixel PNG)"""
    # Minimal PNG file data (1x1 pixel)
    png_data = bytes([
        0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A, 0x00, 0x00, 0x00, 0x0D,
        0x49, 0x48, 0x44, 0x52, 0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x01,
        0x08, 0x02, 0x00, 0x00, 0x00, 0x90, 0x77, 0x53, 0xDE, 0x00, 0x00, 0x00,
        0x0C, 0x49, 0x44, 0x41, 0x54, 0x08, 0x57, 0x63, 0xF8, 0x0F, 0x00, 0x00,
        0x01, 0x00, 0x01, 0x5C, 0xC2, 0x8A, 0x8E, 0x00, 0x00, 0x00, 0x00, 0x49,
        0x45, 0x4E, 0x44, 0xAE, 0x42, 0x60, 0x82
    ])
    return png_data

def test_api_health():
    """Test API health endpoint"""
    print("🔍 Testing API Health...")
    try:
        response = requests.get(f"{API_URL}/health", timeout=10)
        print(f"   Status Code: {response.status_code}")
        print(f"   Response: {response.json()}")
        return response.status_code == 200
    except Exception as e:
        print(f"   ❌ Health check failed: {e}")
        return False

def test_api_root():
    """Test API root endpoint"""
    print("🔍 Testing API Root...")
    try:
        response = requests.get(f"{API_URL}/", timeout=10)
        print(f"   Status Code: {response.status_code}")
        print(f"   Response: {response.json()}")
        return response.status_code == 200
    except Exception as e:
        print(f"   ❌ Root endpoint failed: {e}")
        return False

def test_product_analysis():
    """Test the product analysis endpoint that's failing"""
    print("🔍 Testing Product Analysis Endpoint...")
    
    # Create test image
    image_data = create_test_image()
    
    # Prepare the request
    files = {
        'file': ('test-product.png', BytesIO(image_data), 'image/png')
    }
    data = {
        'language': 'English'
    }
    
    try:
        print(f"   📤 Sending POST request to {API_URL}/generate-product-info")
        print(f"   📄 File size: {len(image_data)} bytes")
        print(f"   🌐 Language: English")
        
        response = requests.post(
            f"{API_URL}/generate-product-info",
            files=files,
            data=data,
            timeout=30
        )
        
        print(f"   📊 Status Code: {response.status_code}")
        print(f"   📋 Headers: {dict(response.headers)}")
        
        # Try to parse JSON response
        try:
            json_response = response.json()
            print(f"   📄 JSON Response: {json.dumps(json_response, indent=2)}")
        except json.JSONDecodeError:
            print(f"   📄 Raw Response: {response.text}")
        
        return response.status_code == 200, response
        
    except Exception as e:
        print(f"   ❌ Product analysis failed: {e}")
        return False, None

def analyze_frontend_expectations():
    """Analyze what the frontend expects from the API"""
    print("🔍 Analyzing Frontend Expectations...")
    
    # Based on the frontend code, the expected response format should be:
    expected_format = {
        "success": True,  # or False
        "data": {
            "title": "string",
            "description": "string", 
            "tags": ["array", "of", "strings"]
        },
        "error": "string (if success is False)"
    }
    
    print("   📋 Expected API Response Format:")
    print(json.dumps(expected_format, indent=4))
    return expected_format

def main():
    """Main debugging function"""
    print("🚀 AI Product Listing Assistant - Analysis Error Debug Tool")
    print("=" * 60)
    
    # Test API health
    health_ok = test_api_health()
    print()
    
    # Test API root
    root_ok = test_api_root()
    print()
    
    # Analyze frontend expectations
    expected_format = analyze_frontend_expectations()
    print()
    
    # Test the failing endpoint
    analysis_ok, response = test_product_analysis()
    print()
    
    # Summary
    print("📊 DIAGNOSTIC SUMMARY:")
    print("=" * 30)
    print(f"   API Health: {'✅ OK' if health_ok else '❌ FAILED'}")
    print(f"   API Root: {'✅ OK' if root_ok else '❌ FAILED'}")
    print(f"   Product Analysis: {'✅ OK' if analysis_ok else '❌ FAILED'}")
    
    if not analysis_ok:
        print("\n🔧 RECOMMENDED ACTIONS:")
        print("   1. Check API response format matches frontend expectations")
        print("   2. Verify error handling in the API endpoint")
        print("   3. Test with different image formats and sizes")
        print("   4. Check Vercel function logs for detailed errors")
    
    return analysis_ok

if __name__ == "__main__":
    main()
