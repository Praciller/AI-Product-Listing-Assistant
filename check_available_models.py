#!/usr/bin/env python3
"""
Check available Gemini models
"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def list_available_models():
    """List all available Gemini models"""
    try:
        import google.generativeai as genai
        
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            print("❌ No API key found")
            return
        
        genai.configure(api_key=api_key)
        
        print("📋 Available Gemini Models:")
        print("=" * 30)
        
        models = genai.list_models()
        for model in models:
            print(f"   • {model.name}")
            if hasattr(model, 'supported_generation_methods'):
                methods = model.supported_generation_methods
                if 'generateContent' in methods:
                    print(f"     ✅ Supports generateContent")
                else:
                    print(f"     ❌ Does not support generateContent")
            print()
        
        # Test common model names
        common_models = [
            'gemini-pro',
            'gemini-pro-vision',
            'gemini-1.5-pro',
            'gemini-1.5-flash',
            'models/gemini-pro',
            'models/gemini-pro-vision',
            'models/gemini-1.5-pro',
            'models/gemini-1.5-flash'
        ]
        
        print("🧪 Testing Common Model Names:")
        print("=" * 35)
        
        for model_name in common_models:
            try:
                model = genai.GenerativeModel(model_name)
                response = model.generate_content("Hello")
                print(f"   ✅ {model_name} - WORKS")
            except Exception as e:
                print(f"   ❌ {model_name} - {str(e)[:50]}...")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    list_available_models()
