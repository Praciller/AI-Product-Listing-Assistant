"""
AI Product Listing Assistant - Streamlit Frontend

A user-friendly web interface for generating AI-powered product listings
from images using Google Gemini AI. Supports multiple languages and
provides optimized titles, descriptions, and tags for e-commerce platforms.

Features:
- Multi-language support (12 languages)
- Image upload and analysis
- AI-generated product content
- Professional styling and UX

Author: AI Product Listing Assistant
Version: 1.0.0
"""

import streamlit as st
import requests
import json
from PIL import Image
import io

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
        border-left: 4px solid #1f77b4;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
        color: #333333 !important;
    }
    .result-card h4 {
        color: #1f77b4 !important;
        margin-bottom: 1rem !important;
        font-weight: 600 !important;
    }
    .result-card p {
        color: #333333 !important;
        margin: 0 !important;
        line-height: 1.6 !important;
    }
    .tag-container {
        display: flex;
        flex-wrap: wrap;
        gap: 0.5rem;
        margin-top: 0.5rem;
    }
    .tag {
        background-color: #1f77b4;
        color: #ffffff !important;
        padding: 0.4rem 0.8rem;
        border-radius: 20px;
        font-size: 0.875rem;
        font-weight: 500;
        border: none;
        display: inline-block;
        margin: 0.2rem;
        box-shadow: 0 2px 4px rgba(31, 119, 180, 0.3);
    }
    .tag:hover {
        background-color: #1565c0;
        transform: translateY(-1px);
        box-shadow: 0 4px 8px rgba(31, 119, 180, 0.4);
        transition: all 0.2s ease;
    }
    .image-container {
        border: 2px solid #e0e0e0;
        border-radius: 12px;
        padding: 1rem;
        background: linear-gradient(135deg, #f5f5f5 0%, #ffffff 100%);
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
        margin: 1rem 0;
        position: relative;
    }
    .image-container::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background: linear-gradient(45deg,
            rgba(255,255,255,0.1) 25%,
            transparent 25%,
            transparent 75%,
            rgba(255,255,255,0.1) 75%),
            linear-gradient(45deg,
            rgba(255,255,255,0.1) 25%,
            transparent 25%,
            transparent 75%,
            rgba(255,255,255,0.1) 75%);
        background-size: 20px 20px;
        background-position: 0 0, 10px 10px;
        border-radius: 12px;
        pointer-events: none;
        z-index: 1;
    }
    .image-info-overlay {
        background: rgba(0, 0, 0, 0.8);
        color: white;
        padding: 0.5rem 1rem;
        border-radius: 8px;
        font-size: 0.875rem;
        font-weight: 500;
        margin-top: 0.5rem;
        backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 255, 255, 0.2);
    }
    /* Improve image caption styling */
    .stImage > div > div > div > div {
        background: rgba(0, 0, 0, 0.7) !important;
        color: white !important;
        padding: 0.5rem 1rem !important;
        border-radius: 0 0 8px 8px !important;
        font-weight: 500 !important;
        backdrop-filter: blur(5px) !important;
    }
    /* Enhance file uploader styling */
    .stFileUploader > div > div > div {
        border: 2px dashed #1f77b4 !important;
        border-radius: 12px !important;
        background: linear-gradient(135deg, #f8f9ff 0%, #ffffff 100%) !important;
    }
    .stFileUploader > div > div > div:hover {
        border-color: #1565c0 !important;
        background: linear-gradient(135deg, #e3f2fd 0%, #f8f9ff 100%) !important;
    }
</style>
""", unsafe_allow_html=True)

def main():
    # Header
    st.markdown('<h1 class="main-header">🛍️ AI Product Listing Assistant</h1>', unsafe_allow_html=True)
    st.markdown(
        '<p style="text-align: center; color: #666; font-size: 1.1rem;">Upload a product image and get AI-generated title, description, and tags instantly!</p>',
        unsafe_allow_html=True
    )
    
    # Sidebar with information
    with st.sidebar:
        st.header("ℹ️ How it works")
        st.markdown("""
        1. **Upload** a product image
        2. **AI analyzes** the image using Google Gemini
        3. **Get** optimized title, description, and tags
        4. **Copy** the results for your e-commerce listing
        """)
        
        st.header("📋 Supported formats")
        st.markdown("""
        - JPG/JPEG
        - PNG
        - GIF
        - BMP
        - WEBP
        """)
        
        st.header("🎯 Best practices")
        st.markdown("""
        - Use clear, well-lit images
        - Show the product prominently
        - Avoid cluttered backgrounds
        - Include multiple angles if possible
        """)
    
    # Main content area
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("📤 Upload Product Image")
        
        # File uploader
        uploaded_file = st.file_uploader(
            "Choose an image file",
            type=['png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp'],
            help="Upload a clear image of your product for best results"
        )

        # Language selection
        st.subheader("🌐 Select Output Language")
        language_options = {
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

        selected_language = st.selectbox(
            "Choose the language for AI-generated content:",
            options=list(language_options.keys()),
            index=0,  # Default to English
            help="Select the language for product title, description, and tags"
        )

        language_code = language_options[selected_language]
        
        if uploaded_file is not None:
            # Display uploaded image with improved styling
            image = Image.open(uploaded_file)

            # Create a styled container for the image
            st.markdown('<div class="image-container">', unsafe_allow_html=True)
            st.image(image, caption="📸 Uploaded Product Image", use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)

            # Image info with better styling
            st.markdown(f"""
            <div class="image-info-overlay">
                📊 <strong>Image Details:</strong> {image.size[0]} × {image.size[1]} pixels | {uploaded_file.type.upper()} | {round(len(uploaded_file.getvalue()) / 1024, 1)} KB
            </div>
            """, unsafe_allow_html=True)
    
    with col2:
        st.subheader("🤖 AI Analysis Results")
        
        if uploaded_file is not None:
            # Analyze button
            if st.button("🔍 Analyze Product", type="primary", use_container_width=True):
                with st.spinner("🧠 AI is analyzing your product image..."):
                    try:
                        # Prepare the file for API request
                        files = {"file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)}
                        data = {"language": language_code}

                        # Make API request to FastAPI backend
                        response = requests.post(
                            "http://localhost:8000/generate-product-info",
                            files=files,
                            data=data,
                            timeout=30
                        )
                        
                        if response.status_code == 200:
                            result = response.json()
                            
                            if result.get("success"):
                                data = result["data"]
                                
                                # Display results in styled cards
                                st.success("✅ Analysis completed successfully!")
                                
                                # Title
                                st.markdown(f"""
                                <div class="result-card">
                                    <h4>📝 Product Title</h4>
                                    <p style="font-size: 1.1rem; font-weight: 500; color: #333333 !important;">{data['title']}</p>
                                </div>
                                """, unsafe_allow_html=True)

                                # Description
                                st.markdown(f"""
                                <div class="result-card">
                                    <h4>📄 Product Description</h4>
                                    <p style="line-height: 1.6; color: #333333 !important;">{data['description']}</p>
                                </div>
                                """, unsafe_allow_html=True)
                                
                                # Tags
                                tags_html = "".join([f'<span class="tag">{tag}</span>' for tag in data['tags']])
                                st.markdown(f"""
                                <div class="result-card">
                                    <h4>🏷️ Product Tags</h4>
                                    <div class="tag-container">
                                        {tags_html}
                                    </div>
                                </div>
                                """, unsafe_allow_html=True)
                                
                                # Copy to clipboard section
                                st.subheader("📋 Copy Results")
                                
                                # Formatted text for copying
                                formatted_text = f"""Title: {data['title']}

Description: {data['description']}

Tags: {', '.join(data['tags'])}"""
                                
                                st.text_area(
                                    "Copy this text for your product listing:",
                                    value=formatted_text,
                                    height=150,
                                    help="Select all and copy (Ctrl+A, Ctrl+C)"
                                )
                                
                                # Download as JSON
                                json_data = json.dumps(data, indent=2)
                                st.download_button(
                                    label="💾 Download as JSON",
                                    data=json_data,
                                    file_name=f"product_info_{uploaded_file.name.split('.')[0]}.json",
                                    mime="application/json"
                                )
                            else:
                                st.error("❌ Failed to analyze the image. Please try again.")
                        else:
                            error_detail = response.json().get("detail", "Unknown error")
                            st.error(f"❌ API Error: {error_detail}")
                            
                    except requests.exceptions.ConnectionError:
                        st.error("❌ Cannot connect to the API server. Make sure the FastAPI server is running on http://localhost:8000")
                    except requests.exceptions.Timeout:
                        st.error("❌ Request timed out. The image might be too large or the server is busy.")
                    except Exception as e:
                        st.error(f"❌ An error occurred: {str(e)}")
        else:
            st.info("👆 Upload an image to start the analysis")
    
    # Footer
    st.markdown("---")
    st.markdown(
        '<p style="text-align: center; color: #888; font-size: 0.9rem;">Built with ❤️ using Streamlit, FastAPI, and Google Gemini AI</p>',
        unsafe_allow_html=True
    )

if __name__ == "__main__":
    main()
