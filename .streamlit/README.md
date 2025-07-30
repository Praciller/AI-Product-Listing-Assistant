# Streamlit Configuration

This folder contains configuration files for the AI Product Listing Assistant Streamlit application.

## Files

### `config.toml`
Contains application configuration settings including:
- Server settings (port, CORS, upload limits)
- Theme configuration (colors, fonts)
- Browser and client settings
- Performance optimizations

### `secrets.toml` (Template)
Template file for environment variables and secrets:
- **IMPORTANT**: This is a template file
- Copy and rename to create your actual secrets file
- Add your Google AI Studio API key
- Never commit the actual secrets file to version control

## Setup Instructions

### For Local Development:
1. Copy `secrets.toml` to create your actual secrets file
2. Add your Google AI Studio API key
3. Run the application with `streamlit run streamlit_app.py`

### For Streamlit Cloud Deployment:
1. The `config.toml` file will be automatically used
2. Add secrets in the Streamlit Cloud dashboard:
   - Go to your app settings
   - Navigate to "Secrets"
   - Add: `GOOGLE_API_KEY = "your_actual_api_key"`

## Configuration Details

The configuration optimizes the application for:
- Better performance with caching enabled
- Professional theme matching the application design
- Proper security settings for production
- Optimized upload limits for product images
- Clean UI without unnecessary Streamlit elements

## Security Notes

- Never commit actual API keys or secrets to version control
- The `.gitignore` file is configured to exclude secrets files
- For production deployment, always use environment variables or secure secret management
