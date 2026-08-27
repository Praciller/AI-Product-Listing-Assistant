#!/usr/bin/env python3
"""AI Product Listing Assistant API with mock and optional external routes."""

import os
import io
import warnings
from typing import Annotated, Literal
from urllib.parse import urlsplit

from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging
from dotenv import load_dotenv
from PIL import Image, UnidentifiedImageError
from pydantic import BaseModel
from product_listing_service import (
    ProductListing,
    ProductListingService,
    ProviderExecutionError,
)

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
# httpx request logs include destination URLs. Keep provider routing telemetry
# classification-only and prevent endpoint details from entering app logs.
logging.getLogger("httpx").setLevel(logging.WARNING)

DEFAULT_CORS_ORIGINS = ["http://localhost:3000", "http://127.0.0.1:3000"]
UPLOAD_CHUNK_SIZE = 64 * 1024
IMAGE_SIGNATURES = {
    "JPEG": lambda data: data.startswith(b"\xff\xd8\xff"),
    "PNG": lambda data: data.startswith(b"\x89PNG\r\n\x1a\n"),
    "WEBP": lambda data: (
        len(data) >= 12 and data.startswith(b"RIFF") and data[8:12] == b"WEBP"
    ),
}
SUPPORTED_IMAGE_TYPES = {
    "image/jpeg": "JPEG",
    "image/png": "PNG",
    "image/webp": "WEBP",
}


def read_bounded_int_setting(name: str, default: int, maximum: int) -> int:
    try:
        value = int(os.getenv(name, str(default)))
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer") from exc
    if not 1 <= value <= maximum:
        raise ValueError(f"{name} must be between 1 and {maximum}")
    return value


MAX_UPLOAD_SIZE_BYTES = read_bounded_int_setting(
    "MAX_UPLOAD_SIZE_BYTES", 5 * 1024 * 1024, 25 * 1024 * 1024
)
MAX_IMAGE_PIXELS = read_bounded_int_setting("MAX_IMAGE_PIXELS", 25_000_000, 50_000_000)


def detect_image_format(data: bytes) -> str | None:
    return next(
        (name for name, matches in IMAGE_SIGNATURES.items() if matches(data)), None
    )


def parse_cors_origins(value: str | None) -> list[str]:
    raw = os.getenv("CORS_ORIGINS", "") if value is None else value
    if not raw.strip():
        return DEFAULT_CORS_ORIGINS.copy()

    origins = []
    for candidate in raw.split(","):
        parsed = urlsplit(candidate.strip())
        if (
            parsed.scheme not in {"http", "https"}
            or not parsed.netloc
            or parsed.username
            or parsed.password
            or parsed.path not in {"", "/"}
            or parsed.query
            or parsed.fragment
        ):
            raise ValueError("CORS_ORIGINS must contain only HTTP(S) origins")
        origin = f"{parsed.scheme.lower()}://{parsed.netloc.lower()}"
        if origin not in origins:
            origins.append(origin)
    return origins


def validate_decodable_image(data: bytes, expected_format: str) -> None:
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(data)) as image:
                if image.format != expected_format:
                    raise ValueError("image format mismatch")
                if image.width * image.height > MAX_IMAGE_PIXELS:
                    raise HTTPException(
                        status_code=422,
                        detail="Image dimensions exceed the configured pixel limit.",
                    )
                image.verify()
            with Image.open(io.BytesIO(data)) as image:
                image.load()
    except (
        Image.DecompressionBombError,
        Image.DecompressionBombWarning,
        UnidentifiedImageError,
        OSError,
        ValueError,
    ) as exc:
        raise HTTPException(
            status_code=422,
            detail="Image content is corrupt or does not match its declared format.",
        ) from exc


async def read_validated_upload(file: UploadFile) -> bytes:
    try:
        media_type = (file.content_type or "").split(";", 1)[0].strip().lower()
        if media_type not in SUPPORTED_IMAGE_TYPES:
            raise HTTPException(
                status_code=415,
                detail="Only JPEG, PNG, and WebP images are supported.",
            )

        image_data = bytearray()
        while chunk := await file.read(
            min(UPLOAD_CHUNK_SIZE, MAX_UPLOAD_SIZE_BYTES + 1 - len(image_data))
        ):
            image_data.extend(chunk)
            if len(image_data) > MAX_UPLOAD_SIZE_BYTES:
                limit_mib = MAX_UPLOAD_SIZE_BYTES / (1024 * 1024)
                limit_label = f"{limit_mib:g} MiB"
                raise HTTPException(
                    status_code=413,
                    detail=f"Image exceeds the {limit_label} upload limit.",
                )

        if not image_data:
            raise HTTPException(
                status_code=400,
                detail="Empty file uploaded. Please select a valid image.",
            )

        payload = bytes(image_data)
        detected_format = detect_image_format(payload)
        if detected_format is None:
            raise HTTPException(
                status_code=422,
                detail="Image content is corrupt or does not match its declared format.",
            )
        if detected_format != SUPPORTED_IMAGE_TYPES[media_type]:
            raise HTTPException(
                status_code=415,
                detail="Image signature does not match its declared media type.",
            )
        validate_decodable_image(payload, detected_format)
        return payload
    finally:
        await file.close()


# Initialize the explicitly selected mock or external service.
product_listing_service = ProductListingService()


class ProductListingResponse(BaseModel):
    success: Literal[True] = True
    data: ProductListing


class ErrorResponse(BaseModel):
    success: Literal[False] = False
    error: str


app = FastAPI(
    title="AI Product Listing Assistant API",
    description="API for generating draft product listings from images",
    version="2.0.0",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=parse_cors_origins(None),
    allow_credentials=False,
    allow_methods=["POST"],
    allow_headers=["Content-Type"],
)


@app.get("/")
async def root():
    """Root endpoint for health check"""
    return {
        "message": "AI Product Listing Assistant API",
        "status": "running",
        "version": "2.0.0",
        "environment": os.environ.get("VERCEL_ENV", "local"),
        "ai_provider": product_listing_service.provider,
        "features": ["mock_first", "optional_image_analysis", "multi_language_output"],
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "ok",
        "message": "API is running",
        "environment": os.environ.get("VERCEL_ENV", "unknown"),
    }


@app.post(
    "/generate-product-info",
    response_model=ProductListingResponse,
    responses={
        400: {"model": ErrorResponse},
        413: {"model": ErrorResponse},
        415: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
async def generate_product_info(
    file: Annotated[UploadFile, File()],
    language: Annotated[str, Form()] = "English",
):
    """Generate product information from uploaded image"""

    try:
        logger.info("Processing image in language %s", language)

        media_type = (file.content_type or "").split(";", 1)[0].strip().lower()
        image_data = await read_validated_upload(file)

        # Analyze image using the explicitly selected inference route.
        logger.info("Starting product analysis (%s bytes)", len(image_data))
        analysis_data = await product_listing_service.analyze_product_image(
            image_data, language, media_type
        )

        logger.info("✅ AI product analysis completed successfully")
        return ProductListingResponse(data=analysis_data)

    except HTTPException as e:
        # Return HTTP exceptions in the format expected by the frontend
        error_response = ErrorResponse(error=e.detail)
        return JSONResponse(
            content=error_response.model_dump(), status_code=e.status_code
        )
    except ProviderExecutionError as exc:
        telemetry = exc.telemetry
        if telemetry is not None:
            logger.warning(
                "External provider degraded route=%s attempts=%s retries=%s "
                "failure=%s fallback=%s degraded=%s circuit=%s",
                telemetry.route,
                telemetry.attempts,
                telemetry.retry_count,
                telemetry.failure_category,
                telemetry.fallback,
                telemetry.degraded,
                telemetry.circuit_state.value,
            )
        else:
            logger.warning("External provider degraded without telemetry")
        error_response = ErrorResponse(
            error="Analysis failed. Check provider configuration and try again."
        )
        return JSONResponse(content=error_response.model_dump(), status_code=500)
    except Exception:
        logger.error("Product analysis failed")
        # Return error in the format expected by the frontend
        error_response = ErrorResponse(
            error="Analysis failed. Check provider configuration and try again."
        )
        return JSONResponse(content=error_response.model_dump(), status_code=500)


if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
