# AI Product Listing Assistant - Makefile

.PHONY: help install test test-unit test-integration test-e2e test-all lint format clean run-api run-streamlit run-all

# Default target
help:
	@echo "Available commands:"
	@echo "  install          Install dependencies"
	@echo "  test             Run all tests"
	@echo "  test-unit        Run unit tests only"
	@echo "  test-integration Run integration tests only"
	@echo "  test-e2e         Run end-to-end tests only"
	@echo "  test-all         Run all tests with coverage"
	@echo "  lint             Run code linting"
	@echo "  format           Format code"
	@echo "  clean            Clean up generated files"
	@echo "  run-api          Run FastAPI server"
	@echo "  run-streamlit    Run Streamlit app"
	@echo "  run-all          Run both servers"

# Install dependencies
install:
	pip install -e .
	pip install tenacity structlog pytest pytest-asyncio httpx playwright pytest-mock pytest-cov respx pytest-xdist black isort mypy ruff
	python -m playwright install

# Test commands
test: test-unit

test-unit:
	pytest tests/unit -v --tb=short

test-integration:
	pytest tests/integration -v --tb=short

test-e2e:
	pytest tests/e2e -v --tb=short -m "e2e and not slow"

test-e2e-all:
	pytest tests/e2e -v --tb=short -m "e2e"

test-all:
	pytest tests/ -v --cov=. --cov-report=term-missing --cov-report=html

# Code quality
lint:
	ruff check .
	mypy main.py services/ --ignore-missing-imports

format:
	black .
	isort .
	ruff format .

# Clean up
clean:
	rm -rf __pycache__/
	rm -rf .pytest_cache/
	rm -rf htmlcov/
	rm -rf .coverage
	rm -rf *.egg-info/
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

# Run servers
run-api:
	python main.py

run-streamlit:
	streamlit run streamlit_app.py

run-all:
	@echo "Starting FastAPI server in background..."
	python main.py &
	@echo "Starting Streamlit app..."
	streamlit run streamlit_app.py
