#!/usr/bin/env python3
"""
Debug script to test Google Gemini API directly
"""

import os
import io
from PIL import Image, ImageDraw
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_api_key():
    """Test if API key is valid"""
    api_key = os.getenv("GOOGLE_API_KEY")
    print(f"🔑 API Key Status:")
    print(f"   Found: {'✅ YES' if api_key else '❌ NO'}")
    if api_key:
        print(f"   Length: {len(api_key)}")
        print(f"   Starts with 'AIza': {'✅ YES' if api_key.startswith('AIza') else '❌ NO'}")
        print(f"   First 10 chars: {api_key[:10]}...")
    return api_key

def test_gemini_import():
    """Test if we can import Google Generative AI"""
    try:
        import google.generativeai as genai
        print("✅ google.generativeai imported successfully")
        return True
    except ImportError as e:
        print(f"❌ Failed to import google.generativeai: {e}")
        return False

def test_gemini_initialization():
    """Test Gemini API initialization"""
    try:
        import google.generativeai as genai
        
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            print("❌ No API key found")
            return False
        
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-flash')
        print("✅ Gemini model initialized successfully")
        return model
    except Exception as e:
        print(f"❌ Failed to initialize Gemini: {e}")
        return False

def test_simple_text_generation(model):
    """Test simple text generation"""
    try:
        response = model.generate_content("Hello, how are you?")
        print("✅ Simple text generation works")
        print(f"   Response: {response.text[:100]}...")
        return True
    except Exception as e:
        print(f"❌ Simple text generation failed: {e}")
        return False

def create_test_image():
    """Create a simple test image"""
    img = Image.new('RGB', (100, 100), color='red')
    draw = ImageDraw.Draw(img)
    draw.rectangle([10, 10, 90, 90], outline='white', width=2)
    return img

def test_vision_analysis(model):
    """Test vision analysis with a simple image"""
    try:
        image = create_test_image()
        
        prompt = "Describe what you see in this image."
        response = model.generate_content([prompt, image])
        
        print("✅ Vision analysis works")
        print(f"   Response: {response.text[:100]}...")
        return True
    except Exception as e:
        print(f"❌ Vision analysis failed: {e}")
        return False

def test_json_response(model):
    """Test JSON-formatted response"""
    try:
        image = create_test_image()
        
        prompt = """
        Analyze this image and respond with JSON format:
        {
          "title": "Product title",
          "description": "Product description",
          "tags": ["tag1", "tag2", "tag3"]
        }
        """
        
        response = model.generate_content([prompt, image])
        
        print("✅ JSON response generation works")
        print(f"   Response: {response.text[:200]}...")
        
        # Try to parse as JSON
        import json
        response_text = response.text.strip()
        if response_text.startswith('```json'):
            response_text = response_text[7:]
        if response_text.endswith('```'):
            response_text = response_text[:-3]
        
        try:
            parsed = json.loads(response_text)
            print("✅ JSON parsing successful")
            print(f"   Parsed: {parsed}")
            return True
        except json.JSONDecodeError:
            print("⚠️  JSON parsing failed, but response received")
            return True
            
    except Exception as e:
        print(f"❌ JSON response failed: {e}")
        return False

def main():
    """Main debug function"""
    print("🔍 Google Gemini API Debug Tool")
    print("=" * 40)
    
    # Test 1: API Key
    api_key = test_api_key()
    print()
    
    if not api_key:
        print("❌ Cannot proceed without API key")
        print("💡 Set GOOGLE_API_KEY in .env file")
        return
    
    # Test 2: Import
    if not test_gemini_import():
        print("❌ Cannot proceed without google.generativeai")
        print("💡 Install with: pip install google-generativeai")
        return
    print()
    
    # Test 3: Initialization
    model = test_gemini_initialization()
    if not model:
        print("❌ Cannot proceed without model initialization")
        return
    print()
    
    # Test 4: Simple text
    if not test_simple_text_generation(model):
        print("❌ Basic functionality not working")
        return
    print()
    
    # Test 5: Vision analysis
    if not test_vision_analysis(model):
        print("❌ Vision analysis not working")
        return
    print()
    
    # Test 6: JSON response
    if not test_json_response(model):
        print("❌ JSON response not working")
        return
    print()
    
    print("🎉 ALL TESTS PASSED!")
    print("✅ Google Gemini API is working correctly")
    print("💡 The issue might be in the service integration")

if __name__ == "__main__":
    main()
