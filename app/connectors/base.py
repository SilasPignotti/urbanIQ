"""
Abstract base class for external data connectors.

Provides common HTTP client functionality, retry logic with exponential backoff,
error handling, and logging for all connector implementations.
"""

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

logger = logging.getLogger("urbaniq.connectors")


class ConnectorError(Exception):
    """Base exception for connector failures."""

    pass


class ServiceUnavailableError(ConnectorError):
    """Raised when external service is unavailable (HTTP 5xx errors)."""

    pass


class InvalidParameterError(ConnectorError):
    """Raised when request parameters are invalid (HTTP 400 errors)."""

    pass


class RateLimitError(ConnectorError):
    """Raised when rate limit is exceeded (HTTP 429 errors)."""

    pass


class BaseConnector(ABC):
    """
    Abstract base class for external data connectors.

    Provides common functionality for HTTP requests, retry logic,
    error handling, and response processing.
    """

    def __init__(self, base_url: str, timeout: float = 30.0) -> None:
        """
        Initialize connector with base configuration.

        Args:
            base_url: Base URL for the external service
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._client_config: Dict[str, Any] = {
            "timeout": httpx.Timeout(timeout),
            "headers": {"User-Agent": "urbanIQ/0.1.0 Berlin Geodata Aggregation System"},
        }

    @retry(
        retry=retry_if_exception_type((httpx.TimeoutException, ServiceUnavailableError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    async def _make_request(
        self, method: str, url: str, params: dict[str, Any] | None = None, **kwargs: Any
    ) -> httpx.Response:
        """
        Make HTTP request with retry logic and error handling.

        Args:
            method: HTTP method (GET, POST, etc.)
            url: Request URL
            params: URL parameters
            **kwargs: Additional request arguments

        Returns:
            HTTP response object

        Raises:
            ServiceUnavailableError: For HTTP 5xx errors
            InvalidParameterError: For HTTP 400 errors
            RateLimitError: For HTTP 429 errors
            ConnectorError: For other HTTP errors
        """
        async with httpx.AsyncClient(**self._client_config) as client:
            try:
                logger.debug(f"Making {method} request to {url} with params: {params}")
                response = await client.request(method, url, params=params, **kwargs)

                # Handle different HTTP status codes
                if response.status_code == 400:
                    error_msg = f"Invalid parameters: {response.text[:200]}"
                    logger.error(error_msg)
                    raise InvalidParameterError(error_msg)
                elif response.status_code == 429:
                    error_msg = "Rate limit exceeded"
                    logger.warning(error_msg)
                    raise RateLimitError(error_msg)
                elif response.status_code >= 500:
                    error_msg = f"Service unavailable (HTTP {response.status_code})"
                    logger.error(error_msg)
                    raise ServiceUnavailableError(error_msg)
                elif response.status_code >= 400:
                    error_msg = f"HTTP error {response.status_code}: {response.text[:200]}"
                    logger.error(error_msg)
                    raise ConnectorError(error_msg)

                response.raise_for_status()
                logger.debug(f"Request successful: {response.status_code}")
                return response

            except httpx.TimeoutException as e:
                error_msg = f"Request timeout after {self.timeout}s"
                logger.error(error_msg)
                raise ServiceUnavailableError(error_msg) from e
            except httpx.HTTPStatusError as e:
                error_msg = f"HTTP status error: {e.response.status_code}"
                logger.error(error_msg)
                raise ConnectorError(error_msg) from e
            except httpx.RequestError as e:
                error_msg = f"Request error: {str(e)}"
                logger.error(error_msg)
                raise ConnectorError(error_msg) from e

    async def _get_json(self, url: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """
        Make GET request and return JSON response.

        Args:
            url: Request URL
            params: URL parameters

        Returns:
            Parsed JSON response

        Raises:
            ConnectorError: If response is not valid JSON
        """
        response = await self._make_request("GET", url, params=params)

        try:
            json_data: Dict[str, Any] = response.json()
            return json_data
        except Exception as e:
            error_msg = f"Failed to parse JSON response: {str(e)}"
            logger.error(error_msg)
            raise ConnectorError(error_msg) from e

    async def _get_text(self, url: str, params: dict[str, Any] | None = None) -> str:
        """
        Make GET request and return text response.

        Args:
            url: Request URL
            params: URL parameters

        Returns:
            Response text content
        """
        response = await self._make_request("GET", url, params=params)
        return response.text

    def _build_url(self, endpoint: str) -> str:
        """
        Build full URL from base URL and endpoint.

        Args:
            endpoint: API endpoint path

        Returns:
            Complete URL
        """
        endpoint = endpoint.lstrip("/")
        return f"{self.base_url}/{endpoint}"

    @abstractmethod
    async def test_connection(self) -> bool:
        """
        Test connection to the external service.

        Returns:
            True if connection is successful, False otherwise

        This method should be implemented by concrete connector classes
        to provide service-specific health checks.
        """
        pass

    async def cleanup(self) -> None:
        """
        Clean up connector resources.

        Default implementation does nothing, but can be overridden
        by concrete classes that need cleanup (e.g., closing connections).
        """
        # Default implementation - no cleanup needed for base connector
        return
