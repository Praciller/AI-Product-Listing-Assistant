"""
Resilient Product Analysis Service - Adds required resiliency patterns.

This resilience layer implements retry logic, circuit breaker patterns, 
and other reliability mechanisms for the product analysis service.
"""

import asyncio
from typing import Dict, Any, Optional
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log
)
from services.product_analysis_manager import ProductAnalysisManager
import structlog

logger = structlog.get_logger(__name__)


class CircuitBreakerError(Exception):
    """Exception raised when circuit breaker is open."""
    pass


class ResilientProductAnalysisService:
    """Resilience layer for product analysis with retry logic and circuit breaker."""
    
    def __init__(
        self, 
        api_key: Optional[str] = None,
        max_retries: int = 3,
        circuit_breaker_threshold: int = 5,
        circuit_breaker_timeout: int = 60
    ):
        """
        Initialize the resilient service.
        
        Args:
            api_key: Google AI API key
            max_retries: Maximum number of retry attempts
            circuit_breaker_threshold: Number of failures before opening circuit
            circuit_breaker_timeout: Seconds to wait before trying to close circuit
        """
        self.manager = ProductAnalysisManager(api_key)
        self.max_retries = max_retries
        self.circuit_breaker_threshold = circuit_breaker_threshold
        self.circuit_breaker_timeout = circuit_breaker_timeout
        
        # Circuit breaker state
        self._failure_count = 0
        self._last_failure_time = 0
        self._circuit_open = False
        
        logger.info(
            "Resilient Product Analysis Service initialized",
            max_retries=max_retries,
            circuit_breaker_threshold=circuit_breaker_threshold,
            circuit_breaker_timeout=circuit_breaker_timeout
        )
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type((ConnectionError, TimeoutError)),
        before_sleep=before_sleep_log(logger, "info")
    )
    def analyze_product_with_retry(
        self,
        image_data: bytes,
        filename: str,
        language: str = "en"
    ) -> Dict[str, Any]:
        """
        Analyze product with retry logic and circuit breaker.
        
        Args:
            image_data: Raw image bytes
            filename: Original filename
            language: Target language for content generation
            
        Returns:
            Dictionary containing analysis results
            
        Raises:
            CircuitBreakerError: If circuit breaker is open
            Exception: For other analysis failures
        """
        try:
            # Check circuit breaker
            self._check_circuit_breaker()
            
            # Perform analysis
            result = self.manager.analyze_product(
                image_data=image_data,
                filename=filename,
                language=language
            )
            
            # Reset failure count on success
            self._on_success()
            
            return result
            
        except Exception as e:
            # Record failure
            self._on_failure()
            
            logger.error(
                "Product analysis failed with retry",
                filename=filename,
                language=language,
                error=str(e),
                failure_count=self._failure_count
            )
            raise
    
    def _check_circuit_breaker(self) -> None:
        """Check if circuit breaker allows the request."""
        import time
        
        current_time = time.time()
        
        # If circuit is open, check if timeout has passed
        if self._circuit_open:
            if current_time - self._last_failure_time < self.circuit_breaker_timeout:
                raise CircuitBreakerError(
                    f"Circuit breaker is open. Try again in "
                    f"{self.circuit_breaker_timeout - (current_time - self._last_failure_time):.1f} seconds"
                )
            else:
                # Try to close circuit (half-open state)
                self._circuit_open = False
                logger.info("Circuit breaker moved to half-open state")
    
    def _on_success(self) -> None:
        """Handle successful request."""
        if self._failure_count > 0 or self._circuit_open:
            logger.info(
                "Service recovered",
                previous_failure_count=self._failure_count,
                was_circuit_open=self._circuit_open
            )
        
        self._failure_count = 0
        self._circuit_open = False
    
    def _on_failure(self) -> None:
        """Handle failed request."""
        import time
        
        self._failure_count += 1
        self._last_failure_time = time.time()
        
        # Open circuit if threshold reached
        if self._failure_count >= self.circuit_breaker_threshold:
            self._circuit_open = True
            logger.warning(
                "Circuit breaker opened",
                failure_count=self._failure_count,
                threshold=self.circuit_breaker_threshold
            )
    
    def get_circuit_breaker_status(self) -> Dict[str, Any]:
        """Get current circuit breaker status."""
        import time
        
        return {
            "circuit_open": self._circuit_open,
            "failure_count": self._failure_count,
            "threshold": self.circuit_breaker_threshold,
            "last_failure_time": self._last_failure_time,
            "time_until_retry": max(
                0, 
                self.circuit_breaker_timeout - (time.time() - self._last_failure_time)
            ) if self._circuit_open else 0
        }
    
    def reset_circuit_breaker(self) -> None:
        """Manually reset the circuit breaker."""
        self._failure_count = 0
        self._circuit_open = False
        self._last_failure_time = 0
        
        logger.info("Circuit breaker manually reset")
    
    def health_check(self) -> Dict[str, Any]:
        """Perform comprehensive health check."""
        try:
            # Get manager health check
            manager_health = self.manager.health_check()
            
            # Add resilience layer status
            circuit_status = self.get_circuit_breaker_status()
            
            overall_status = "healthy"
            if manager_health["status"] != "healthy" or circuit_status["circuit_open"]:
                overall_status = "degraded" if circuit_status["circuit_open"] else "unhealthy"
            
            return {
                "status": overall_status,
                "manager": manager_health,
                "circuit_breaker": circuit_status,
                "resilience_config": {
                    "max_retries": self.max_retries,
                    "circuit_breaker_threshold": self.circuit_breaker_threshold,
                    "circuit_breaker_timeout": self.circuit_breaker_timeout
                }
            }
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e)
            }
    
    # Delegate methods to manager
    def get_supported_languages(self) -> Dict[str, str]:
        """Get supported languages."""
        return self.manager.get_supported_languages()
    
    def validate_language(self, language: str) -> bool:
        """Validate language support."""
        return self.manager.validate_language(language)
