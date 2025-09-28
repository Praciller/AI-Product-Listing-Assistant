"""
AI Product Listing Assistant - Streamlit Cloud Version

A standalone Streamlit application for generating AI-powered product listings
from images using Google Gemini AI. This version integrates the AI functionality
directly without requiring a separate FastAPI backend.

Features:
- Multi-language support (12 languages)
- Image upload and analysis
- AI-generated product content
- Professional styling and UX
- Standalone deployment ready

Author: AI Product Listing Assistant
Version: 2.0.0 (Cloud Ready)
"""

import streamlit as st
import google.generativeai as genai
import json
import os
from PIL import Image
import io
import base64

# Configure Streamlit page settings
st.set_page_config(
    page_title="AI Product Listing Assistant",
    page_icon="🛍️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        text-align: center;
        color: #1f77b4;
        margin-bottom: 2rem;
    }
    .upload-section {
        border: 2px dashed #cccccc;
        border-radius: 10px;
        padding: 2rem;
        text-align: center;
        margin: 1rem 0;
    }
    .result-card {
        background-color: #ffffff;
        border: 1px solid #e0e0e0;
        border-radius: 12px;
        padding: 1.5rem;
        margin: 1rem 0;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .language-selector {
        margin-bottom: 1rem;
    }
    .analyze-button {
        background-color: #1f77b4;
        color: white;
        border: none;
        padding: 0.75rem 2rem;
        border-radius: 8px;
        font-size: 1.1rem;
        font-weight: bold;
        cursor: pointer;
        width: 100%;
        margin: 1rem 0;
    }
    .sidebar-content {
        padding: 1rem;
    }
    .feature-item {
        display: flex;
        align-items: center;
        margin: 0.5rem 0;
    }
    .feature-icon {
        margin-right: 0.5rem;
        font-size: 1.2rem;
    }
</style>
""", unsafe_allow_html=True)

# Supported languages
SUPPORTED_LANGUAGES = {
    "English": "en",
    "ไทย (Thai)": "th", 
    "中文 (Chinese)": "zh",
    "日本語 (Japanese)": "ja",
    "한국어 (Korean)": "ko",
    "Español (Spanish)": "es",
    "Français (French)": "fr",
    "Deutsch (German)": "de",
    "Italiano (Italian)": "it",
    "Português (Portuguese)": "pt",
    "Русский (Russian)": "ru",
    "العربية (Arabic)": "ar"
}

def initialize_gemini():
    """Initialize Google Gemini AI with API key."""
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        st.error("🔑 Google API Key not found! Please set the GOOGLE_API_KEY environment variable.")
        st.info("Get your API key from: https://aistudio.google.com/app/apikey")
        return None
    
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-2.0-flash-exp')
        return model
    except Exception as e:
        st.error(f"❌ Failed to initialize Gemini AI: {str(e)}")
        return None

def create_prompt(language_code: str) -> str:
    """Create a language-specific prompt for product analysis."""
    language_instructions = {
        "en": "in English",
        "th": "in Thai language (ภาษาไทย)",
        "zh": "in Chinese language (中文)",
        "ja": "in Japanese language (日本語)",
        "ko": "in Korean language (한국어)",
        "es": "in Spanish language (Español)",
        "fr": "in French language (Français)",
        "de": "in German language (Deutsch)",
        "it": "in Italian language (Italiano)",
        "pt": "in Portuguese language (Português)",
        "ru": "in Russian language (Русский)",
        "ar": "in Arabic language (العربية)"
    }
    
    lang_instruction = language_instructions.get(language_code, "in English")
    
    return f"""
    Analyze this product image and generate e-commerce listing content {lang_instruction}.
    
    Please provide a JSON response with exactly these fields:
    {{
        "title": "A catchy, SEO-friendly product title (max 60 characters)",
        "description": "A compelling product description highlighting key features and benefits (2-3 sentences)",
        "tags": ["tag1", "tag2", "tag3", "tag4", "tag5"]
    }}
    
    Requirements:
    - Title: Concise, descriptive, under 60 characters
    - Description: Highlight key features, benefits, and appeal to target customers
    - Tags: Exactly 5 relevant keywords for searchability
    - All content must be {lang_instruction}
    - Response must be valid JSON only, no additional text
    """

def analyze_product_image(model, image, language_code: str):
    """Analyze product image using Gemini AI."""
    try:
        # Create prompt
        prompt = create_prompt(language_code)
        
        # Analyze image
        response = model.generate_content([prompt, image])
        
        # Parse response
        response_text = response.text.strip()
        
        # Clean up response (remove markdown formatting if present)
        if response_text.startswith("```json"):
            response_text = response_text[7:]
        if response_text.endswith("```"):
            response_text = response_text[:-3]
        response_text = response_text.strip()
        
        # Parse JSON
        try:
            result = json.loads(response_text)
            
            # Validate required fields
            required_fields = ["title", "description", "tags"]
            for field in required_fields:
                if field not in result:
                    raise ValueError(f"Missing required field: {field}")
            
            # Validate tags
            if not isinstance(result["tags"], list) or len(result["tags"]) != 5:
                raise ValueError("Tags must be a list of exactly 5 items")
            
            return {
                "success": True,
                "data": result
            }
            
        except json.JSONDecodeError as e:
            return {
                "success": False,
                "error": f"Failed to parse AI response as JSON: {str(e)}"
            }
        except ValueError as e:
            return {
                "success": False,
                "error": str(e)
            }
            
    except Exception as e:
        return {
            "success": False,
            "error": f"AI analysis failed: {str(e)}"
        }

def main():
    """Main Streamlit application."""
    
    # Header
    st.markdown('<h1 class="main-header">🛍️ AI Product Listing Assistant</h1>', unsafe_allow_html=True)
    st.markdown('<p style="text-align: center; color: #666; font-size: 1.1rem;">Generate professional product listings from images using AI</p>', unsafe_allow_html=True)
    
    # Initialize Gemini AI
    model = initialize_gemini()
    if not model:
        st.stop()
    
    # Sidebar
    with st.sidebar:
        st.markdown('<div class="sidebar-content">', unsafe_allow_html=True)
        
        st.markdown("### 🌟 How it works")
        st.markdown("""
        <div class="feature-item">
            <span class="feature-icon">📤</span>
            <span>Upload a product image</span>
        </div>
        <div class="feature-item">
            <span class="feature-icon">🌐</span>
            <span>Select your language</span>
        </div>
        <div class="feature-item">
            <span class="feature-icon">🤖</span>
            <span>AI analyzes the image</span>
        </div>
        <div class="feature-item">
            <span class="feature-icon">✨</span>
            <span>Get optimized content</span>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("### 📋 Supported formats")
        st.markdown("• JPG/JPEG\n• PNG\n• WebP\n• GIF")
        
        st.markdown("### 🌍 Languages")
        st.markdown(f"**{len(SUPPORTED_LANGUAGES)}** languages supported")
        
        st.markdown("### ℹ️ About")
        st.markdown("Powered by Google Gemini AI")
        st.markdown("Built with Streamlit")
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Main content
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.markdown("### 📤 Upload Product Image")
        
        # Language selection
        st.markdown('<div class="language-selector">', unsafe_allow_html=True)
        selected_language = st.selectbox(
            "🌐 Select Language",
            options=list(SUPPORTED_LANGUAGES.keys()),
            index=0,
            help="Choose the language for generated content"
        )
        language_code = SUPPORTED_LANGUAGES[selected_language]
        st.markdown('</div>', unsafe_allow_html=True)
        
        # File upload
        uploaded_file = st.file_uploader(
            "Choose an image file",
            type=['png', 'jpg', 'jpeg', 'webp', 'gif'],
            help="Upload a clear product image for best results"
        )
        
        if uploaded_file is not None:
            # Display uploaded image
            image = Image.open(uploaded_file)
            st.image(image, caption="Uploaded Image", use_column_width=True)
            
            # Image details
            st.markdown("**Image Details:**")
            st.write(f"• **Filename:** {uploaded_file.name}")
            st.write(f"• **Size:** {image.size[0]} x {image.size[1]} pixels")
            st.write(f"• **Format:** {image.format}")
            st.write(f"• **File size:** {len(uploaded_file.getvalue()) / 1024:.1f} KB")
    
    with col2:
        st.markdown("### 🔍 Analysis Results")
        
        if uploaded_file is not None:
            # Analyze button
            if st.button("🔍 Analyze Product", type="primary", use_container_width=True):
                with st.spinner("🤖 AI is analyzing your product image..."):
                    # Analyze the image
                    result = analyze_product_image(model, image, language_code)
                    
                    if result["success"]:
                        data = result["data"]
                        
                        # Display results
                        st.success("✅ Analysis completed successfully!")
                        
                        # Title
                        st.markdown('<div class="result-card">', unsafe_allow_html=True)
                        st.markdown("#### 📝 Product Title")
                        st.markdown(f"**{data['title']}**")
                        st.markdown('</div>', unsafe_allow_html=True)
                        
                        # Description
                        st.markdown('<div class="result-card">', unsafe_allow_html=True)
                        st.markdown("#### 📄 Product Description")
                        st.markdown(data['description'])
                        st.markdown('</div>', unsafe_allow_html=True)
                        
                        # Tags
                        st.markdown('<div class="result-card">', unsafe_allow_html=True)
                        st.markdown("#### 🏷️ Product Tags")
                        tags_display = " • ".join([f"`{tag}`" for tag in data['tags']])
                        st.markdown(tags_display)
                        st.markdown('</div>', unsafe_allow_html=True)
                        
                        # Copy-friendly format
                        st.markdown("#### 📋 Copy-Friendly Format")
                        copy_text = f"""**Title:** {data['title']}

**Description:** {data['description']}

**Tags:** {', '.join(data['tags'])}"""
                        
                        st.text_area(
                            "Copy this content:",
                            value=copy_text,
                            height=150,
                            help="Select all and copy to use in your e-commerce platform"
                        )
                        
                    else:
                        st.error(f"❌ {result['error']}")
        else:
            st.info("👆 Upload an image to start the analysis")
    
    # Footer
    st.markdown("---")
    st.markdown(
        '<p style="text-align: center; color: #888; font-size: 0.9rem;">'
        'Made with ❤️ for e-commerce sellers worldwide | '
        'Powered by Google Gemini AI'
        '</p>',
        unsafe_allow_html=True
    )

if __name__ == "__main__":
    main()
