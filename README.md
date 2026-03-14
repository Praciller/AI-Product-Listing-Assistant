# 🛍️ AI Product Listing Assistant

An intelligent e-commerce tool that automatically generates product titles, descriptions, and tags from product images using Google's Gemini AI. Now with **multi-language support** for global e-commerce platforms!

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://ai-product-listing-assistant.vercel.app/)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)](https://fastapi.tiangolo.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## ✨ Features

- **🖼️ Image Analysis**: Upload product images and get instant AI analysis
- **🌐 Multi-Language Support**: Generate content in 12 languages including English, Thai, Chinese, Japanese, Korean, Spanish, French, German, Italian, Portuguese, Russian, and Arabic
- **📝 Smart Titles**: Generate catchy, SEO-friendly product names (max 60 characters)
- **📄 Rich Descriptions**: Create compelling product descriptions highlighting key features
- **🏷️ Relevant Tags**: Automatically generate 5 relevant keywords for better searchability
- **🎨 Beautiful UI**: Clean, responsive Streamlit interface with improved contrast and styling
- **⚡ Fast API**: High-performance FastAPI backend with CORS support
- **📱 Mobile Friendly**: Works perfectly on desktop and mobile devices
- **☁️ Cloud Ready**: Optimized for Streamlit Cloud deployment

## 🏗️ Architecture

The application follows a modern three-layer architecture with enterprise-grade resilience patterns:

```
┌─────────────────┐    HTTP     ┌─────────────────┐    API     ┌─────────────────┐
│   Streamlit     │ ────────────▶│    FastAPI      │ ──────────▶│   Google        │
│   Frontend      │              │    Backend      │            │   Gemini AI     │
│                 │◀──────────── │                 │◀────────── │                 │
└─────────────────┘   Response   └─────────────────┘  Response  └─────────────────┘
```

### Service Layers

1. **Service Layer** (`GeminiService`): Core AI integration and image processing
2. **Manager Layer** (`ProductAnalysisManager`): Business logic and validation
3. **Resilience Layer** (`ResilientProductAnalysisService`): Retry logic and circuit breaker patterns

### Key Features

- **Circuit Breaker Pattern**: Prevents cascading failures
- **Retry Logic**: Automatic retry with exponential backoff
- **Structured Logging**: JSON-formatted logs with contextual information
- **Health Checks**: Comprehensive service health monitoring
- **Type Safety**: Full type hints for better code quality

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- [uv](https://docs.astral.sh/uv/) package manager
- Google AI Studio API key

### 1. Clone the Repository

```bash
git clone <your-repo-url>
cd AI-Product-Listing-Assistant
```

### 2. Install Dependencies

```bash
uv sync
```

### 3. Set Up Environment Variables

1. Copy the example environment file:

```bash
cp .env.example .env
```

2. Get your Google AI Studio API key:

   - Go to [Google AI Studio](https://aistudio.google.com/app/apikey)
   - Create a new API key
   - Copy the key

3. Edit `.env` file and add your API key:

```bash
GOOGLE_API_KEY=your_actual_api_key_here
```

### 4. Run the Application

#### Option A: Run Both Services Separately

**Terminal 1 - Start FastAPI Backend:**

```bash
uv run python main.py
```

The API will be available at `http://localhost:8000`

**Terminal 2 - Start Streamlit Frontend:**

```bash
uv run streamlit run streamlit_app.py
```

The web app will be available at `http://localhost:8501`

#### Option B: Use the Run Script (Coming Soon)

```bash
uv run python run_app.py
```

## 📖 Usage

1. **Open the Web Interface**: Navigate to `http://localhost:8501`
2. **Select Language**: Choose your preferred language from the dropdown (supports 12 languages)
3. **Upload an Image**: Click "Choose an image file" and select a product photo
4. **Analyze**: Click the "🔍 Analyze Product" button
5. **Get Results**: View the AI-generated title, description, and tags in your selected language
6. **Copy Results**: Use the generated content for your e-commerce listings

### 🌐 Supported Languages

| Language   | Code | Native Name |
| ---------- | ---- | ----------- |
| English    | `en` | English     |
| Thai       | `th` | ไทย         |
| Chinese    | `zh` | 中文        |
| Japanese   | `ja` | 日本語      |
| Korean     | `ko` | 한국어      |
| Spanish    | `es` | Español     |
| French     | `fr` | Français    |
| German     | `de` | Deutsch     |
| Italian    | `it` | Italiano    |
| Portuguese | `pt` | Português   |
| Russian    | `ru` | Русский     |
| Arabic     | `ar` | العربية     |

## 🛠️ API Documentation

### Endpoints

#### `GET /`

Health check endpoint.

**Response:**

```json
{
  "message": "AI Product Listing Assistant API is running!"
}
```

#### `GET /health`

Comprehensive health check with service status.

**Response:**

```json
{
  "status": "healthy",
  "message": "All services operational",
  "timestamp": "2024-01-01T12:00:00Z"
}
```

#### `GET /languages`

Get supported languages.

**Response:**

```json
{
  "success": true,
  "languages": {
    "en": "English",
    "th": "Thai",
    "zh": "Chinese"
  },
  "count": 3
}
```

#### `GET /circuit-breaker/status`

Get circuit breaker status.

**Response:**

```json
{
  "success": true,
  "circuit_breaker": {
    "circuit_open": false,
    "failure_count": 0,
    "threshold": 5
  }
}
```

#### `POST /circuit-breaker/reset`

Reset the circuit breaker.

**Response:**

```json
{
  "success": true,
  "message": "Circuit breaker reset successfully"
}
```

#### `POST /generate-product-info`

Analyze a product image and generate listing information in the specified language.

**Request:**

- Method: `POST`
- Content-Type: `multipart/form-data`
- Body:
  - `file`: Image file (required)
  - `language`: Language code (optional, default: "en")

**Example Request:**

```bash
curl -X POST "http://localhost:8000/generate-product-info" \
     -H "accept: application/json" \
     -H "Content-Type: multipart/form-data" \
     -F "file=@product_image.jpg" \
     -F "language=th"
```

**Response:**

```json
{
  "success": true,
  "data": {
    "title": "เสื้อแจ็คเก็ตยีนส์สีน้ำเงิน - ทรงคลาสสิค",
    "description": "เสื้อแจ็คเก็ตยีนส์สีน้ำเงินคลาสสิคที่มีทรงพอดีตัว ทำจากผ้าฝ้ายคุณภาพสูง เหมาะสำหรับการใส่เป็นชั้นนอกและการออกไปเที่ยวแบบลำลอง มอบทั้งสไตล์และความสะดวกสบายด้วยการออกแบบที่ทนทานและดูดีได้หลากหลายโอกาส",
    "tags": ["ยีนส์", "แจ็คเก็ต", "ลำลอง", "สีน้ำเงิน", "ฝ้าย"]
  },
  "filename": "product_image.jpg"
}
```

### Interactive API Documentation

When the FastAPI server is running, visit:

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## 📁 Project Structure

```
AI-Product-Listing-Assistant/
├── main.py                          # FastAPI backend server
├── streamlit_app.py                 # Streamlit frontend application
├── services/                        # Service layer modules
│   ├── __init__.py
│   ├── gemini_service.py           # Core Gemini AI integration
│   ├── product_analysis_manager.py # Business logic layer
│   └── resilient_product_analysis_service.py # Resilience layer
├── tests/                          # Comprehensive test suite
│   ├── __init__.py
│   ├── conftest.py                 # Test configuration and fixtures
│   ├── unit/                       # Unit tests
│   │   ├── __init__.py
│   │   ├── test_gemini_service.py
│   │   └── test_product_analysis_manager.py
│   ├── integration/                # Integration tests
│   │   ├── __init__.py
│   │   └── test_api_endpoints.py
│   └── e2e/                        # End-to-end tests
│       ├── __init__.py
│       └── test_streamlit_app.py
├── pyproject.toml                  # Project dependencies and metadata
├── pytest.ini                     # Pytest configuration
├── Makefile                        # Development commands
├── .env                           # Environment variables (not in git)
├── .env.example                   # Environment variables template
├── .gitignore                     # Git ignore file
└── README.md                      # This file
```

## ☁️ Deployment on Streamlit Cloud

### Prerequisites for Deployment

1. **GitHub Repository**: Your code must be in a public GitHub repository
2. **Google API Key**: You'll need a Google AI Studio API key
3. **Streamlit Cloud Account**: Sign up at [share.streamlit.io](https://share.streamlit.io)

### Step-by-Step Deployment

1. **Prepare Your Repository**:

   ```bash
   # Ensure you have requirements.txt for Streamlit Cloud
   pip freeze > requirements.txt

   # Or use uv to generate requirements.txt
   uv pip compile pyproject.toml -o requirements.txt
   ```

2. **Push to GitHub**:

   ```bash
   git add .
   git commit -m "Prepare for Streamlit Cloud deployment"
   git push origin main
   ```

3. **Deploy on Streamlit Cloud**:

   - Go to [share.streamlit.io](https://share.streamlit.io)
   - Click "New app"
   - Connect your GitHub repository
   - Set the main file path: `streamlit_app.py`
   - Add environment variables in the "Advanced settings":
     - `GOOGLE_API_KEY`: Your Google AI Studio API key

4. **Configure Environment Variables**:
   In Streamlit Cloud's advanced settings, add:
   ```
   GOOGLE_API_KEY = "your_actual_api_key_here"
   ```

### Important Notes for Cloud Deployment

- **Backend Integration**: The current setup runs FastAPI and Streamlit separately. For Streamlit Cloud deployment, you may need to:

  - Use a cloud-hosted FastAPI backend (e.g., Railway, Render, or Heroku)
  - Or integrate the AI functionality directly into the Streamlit app
  - Update the API endpoint URL in `streamlit_app.py`

- **Dependencies**: Ensure all dependencies are listed in `requirements.txt`
- **Secrets Management**: Never commit API keys to your repository

## 🧪 Testing

The project includes a comprehensive test suite with unit, integration, and end-to-end tests.

### Test Structure

- **Unit Tests**: Test individual components in isolation
- **Integration Tests**: Test API endpoints with real HTTP requests
- **End-to-End Tests**: Test complete user workflows using Playwright

### Running Tests

#### All Tests

```bash
make test-all
```

#### Unit Tests Only

```bash
make test-unit
# or
pytest tests/unit -v
```

#### Integration Tests Only

```bash
make test-integration
# or
pytest tests/integration -v
```

#### End-to-End Tests Only

```bash
make test-e2e
# or
pytest tests/e2e -v -m "e2e and not slow"
```

#### With Coverage Report

```bash
pytest tests/ -v --cov=. --cov-report=term-missing --cov-report=html
```

### Test Features

- **Mocked AI Responses**: Tests don't require actual API calls
- **Fixture-based Setup**: Reusable test components
- **Comprehensive Coverage**: Tests cover success and error scenarios
- **Browser Automation**: E2E tests use Playwright for real browser testing
- **Parallel Execution**: Tests can run in parallel for faster feedback

### Manual Testing

1. Start both the FastAPI backend and Streamlit frontend
2. Upload a clear product image
3. Verify that the AI generates relevant title, description, and tags
4. Test with different types of products (clothing, electronics, accessories, etc.)

### API Testing

You can test the API directly using curl:

```bash
curl -X POST "http://localhost:8000/generate-product-info" \
     -H "accept: application/json" \
     -H "Content-Type: multipart/form-data" \
     -F "file=@path/to/your/image.jpg"
```

## 🔧 Configuration

### Environment Variables

| Variable         | Description              | Required | Default   |
| ---------------- | ------------------------ | -------- | --------- |
| `GOOGLE_API_KEY` | Google AI Studio API key | Yes      | -         |
| `FASTAPI_HOST`   | FastAPI server host      | No       | `0.0.0.0` |
| `FASTAPI_PORT`   | FastAPI server port      | No       | `8000`    |
| `STREAMLIT_PORT` | Streamlit server port    | No       | `8501`    |

### Customizing AI Prompts

You can modify the AI prompt in `main.py` to customize the output format or style:

```python
prompt = """
Your custom prompt here...
"""
```

## 🚨 Troubleshooting

### Common Issues

1. **"Cannot connect to the API server"**

   - Make sure the FastAPI server is running on port 8000
   - Check if the port is already in use

2. **"GOOGLE_API_KEY environment variable is required"**

   - Ensure you've created a `.env` file with your API key
   - Verify the API key is valid and has proper permissions

3. **"Invalid image file"**

   - Ensure the uploaded file is a valid image format
   - Try with a different image or check file corruption

4. **"Failed to parse AI response as JSON"**
   - This might be a temporary issue with the AI model
   - Try again with a clearer image or different prompt

### Getting Help

- Check the [Issues](https://github.com/your-repo/issues) page
- Review the API documentation at `http://localhost:8000/docs`
- Ensure all dependencies are properly installed with `uv sync`

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [Google Gemini AI](https://ai.google.dev/) for powerful image analysis
- [FastAPI](https://fastapi.tiangolo.com/) for the robust backend framework
- [Streamlit](https://streamlit.io/) for the beautiful frontend interface
- [iMaterialist Fashion 2021](https://www.kaggle.com/c/imaterialist-fashion-2021-fgvc8) for the sample dataset

## 📊 Tech Stack

### Core Technologies

- **Backend**: Python, FastAPI, Uvicorn
- **Frontend**: Streamlit
- **AI**: Google Gemini 2.0 Flash
- **Package Management**: uv
- **Image Processing**: PIL (Pillow)
- **HTTP Client**: Requests

### Development & Testing

- **Testing Framework**: pytest
- **Test Types**: Unit, Integration, E2E
- **Browser Testing**: Playwright
- **Mocking**: pytest-mock, unittest.mock
- **Coverage**: pytest-cov
- **HTTP Testing**: httpx, respx

### Architecture & Patterns

- **Resilience**: Circuit Breaker, Retry Logic
- **Logging**: Structured logging with structlog
- **Validation**: Pydantic models
- **Error Handling**: Tenacity for retries
- **Type Safety**: Full type hints with mypy

### Code Quality

- **Formatting**: Black, isort
- **Linting**: Ruff, mypy
- **Build System**: Modern pyproject.toml
- **Task Runner**: Make for development commands

---

Made with ❤️ for e-commerce sellers worldwide
