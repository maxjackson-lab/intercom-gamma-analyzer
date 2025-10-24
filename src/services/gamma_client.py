"""
Gamma client for generating presentations using verified v0.2 API.
"""

import asyncio
import time
import random
import structlog
from typing import Dict, List, Any, Optional
import httpx

from src.config.settings import settings

logger = structlog.get_logger()


class GammaClient:
    """Client for Gamma presentation generation using v0.2 API."""

    def __init__(
        self,
        max_total_wait_seconds: int = 480,  # 8 minutes default total timeout
        max_polls: int = 30,
        poll_interval: float = 2.0,
        jitter: bool = True,
        max_5xx_retries: int = 3
    ):
        """
        Initialize Gamma client with configurable retry/timeout parameters.

        Args:
            max_total_wait_seconds: Total timeout for polling (default 8 minutes)
            max_polls: Maximum polling attempts
            poll_interval: Initial poll interval in seconds
            jitter: Enable exponential backoff with jitter
            max_5xx_retries: Maximum retries for 5xx errors
        """
        self.api_key = settings.gamma_api_key
        self.base_url = "https://public-api.gamma.app/v0.2"
        self.timeout = 60
        self.max_polls = max_polls
        self.poll_interval = poll_interval
        self.max_total_wait_seconds = max_total_wait_seconds
        self.jitter = jitter
        self.max_5xx_retries = max_5xx_retries

        self.headers = {
            'X-API-KEY': self.api_key,
            'Content-Type': 'application/json'
        } if self.api_key else {}

        self.logger = structlog.get_logger()

        self.logger.info(
            "gamma_client_initialized",
            api_key_present=bool(self.api_key),
            base_url=self.base_url,
            max_total_wait_seconds=max_total_wait_seconds,
            max_polls=max_polls
        )
    
    async def test_connection(self) -> bool:
        """Test connection to Gamma API."""
        if not self.api_key:
            self.logger.warning("Gamma API key not provided - connection test failed")
            return False
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                # Test with a simple generation request
                test_payload = {
                    "inputText": "Test connection",
                    "format": "presentation",
                    "numCards": 1
                }
                response = await client.post(
                    f"{self.base_url}/generations",
                    headers=self.headers,
                    json=test_payload
                )
                response.raise_for_status()
                self.logger.info("Gamma API connection successful")
                return True
        except Exception as e:
            self.logger.error("Gamma API connection failed", error=str(e), exc_info=True)
            raise
    
    async def generate_presentation(
        self,
        input_text: str,
        format: str = "presentation",
        num_cards: int = 10,
        text_mode: str = "generate",
        card_split: str = "auto",
        theme_name: Optional[str] = None,
        export_as: Optional[str] = None,
        additional_instructions: Optional[str] = None,
        image_options: Optional[Dict] = None,
        text_options: Optional[Dict] = None,
        card_options: Optional[Dict] = None,
        sharing_options: Optional[Dict] = None
    ) -> str:
        """
        Generate a Gamma presentation and return generation ID for polling.
        
        Args:
            input_text: Content for presentation (1-750,000 characters)
            format: "presentation", "document", or "social"
            num_cards: Number of slides (1-60 for Pro, 1-75 for Ultra)
            text_mode: "generate", "condense", or "preserve"
            export_as: "pdf" or "pptx" for direct download
            additional_instructions: Custom instructions (1-500 chars)
            image_options: Image generation settings
            
        Returns:
            Generation ID for polling
            
        Raises:
            GammaAPIError: If generation request fails
        """
        if not self.api_key:
            raise GammaAPIError("Gamma API key not provided")
        
        if len(input_text) < 1 or len(input_text) > 750000:
            raise GammaAPIError(f"Input text must be 1-750,000 characters, got {len(input_text)}")
        
        self.logger.info(
            "gamma_generate_request_start",
            input_text_length=len(input_text),
            format=format,
            num_cards=num_cards,
            text_mode=text_mode,
            export_as=export_as
        )
        
        start_time = time.time()
        
        # Build request payload according to Gamma API v0.2 spec
        payload = {
            "inputText": input_text,
            "format": format,
            "numCards": num_cards,
            "textMode": text_mode,
            "cardSplit": card_split
        }
        
        if theme_name:
            payload["themeName"] = theme_name
        
        if export_as:
            payload["exportAs"] = export_as
        
        if additional_instructions:
            payload["additionalInstructions"] = additional_instructions[:500]
        
        if text_options:
            payload["textOptions"] = text_options
        
        if image_options:
            payload["imageOptions"] = image_options
        
        if card_options:
            payload["cardOptions"] = card_options
        
        if sharing_options:
            payload["sharingOptions"] = sharing_options
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/generations",
                    headers=self.headers,
                    json=payload
                )
                response.raise_for_status()
                
                result = response.json()
                generation_id = result.get('generationId')
                
                if not generation_id:
                    raise GammaAPIError("No generationId returned from API")
                
                elapsed_time_ms = (time.time() - start_time) * 1000
                
                self.logger.info(
                    "gamma_generate_request_success",
                    generation_id=generation_id,
                    response_time_ms=elapsed_time_ms,
                    input_length=len(input_text),
                    num_cards=num_cards
                )
                
                return generation_id
                
        except httpx.HTTPStatusError as e:
            self.logger.error(
                "gamma_api_error",
                status_code=e.response.status_code,
                error_body=e.response.text,
                exc_info=True
            )
            raise GammaAPIError(f"Gamma API error {e.response.status_code}: {e.response.text}")
        except Exception as e:
            self.logger.error(
                "gamma_generate_request_failed",
                error=str(e),
                exc_info=True
            )
            raise GammaAPIError(f"Failed to generate presentation: {e}")
    
    async def get_generation_status(
        self,
        generation_id: str,
        retry_count: int = 0
    ) -> Dict[str, Any]:
        """
        Get the status of a generation request with retry logic for 5xx errors.

        Args:
            generation_id: ID returned from generate_presentation
            retry_count: Current retry attempt (internal use)

        Returns:
            Status dictionary with generation details

        Raises:
            GammaAPIError: If status check fails
        """
        if not self.api_key:
            raise GammaAPIError("Gamma API key not provided")

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.base_url}/generations/{generation_id}",
                    headers=self.headers
                )
                response.raise_for_status()

                result = response.json()

                self.logger.debug(
                    "gamma_generation_status_checked",
                    generation_id=generation_id,
                    status=result.get('status')
                )

                return result

        except httpx.HTTPStatusError as e:
            status_code = e.response.status_code

            # Handle 5xx errors with retries
            if 500 <= status_code < 600 and retry_count < self.max_5xx_retries:
                retry_wait = self._calculate_backoff(retry_count, base=2.0, max_wait=30)
                self.logger.warning(
                    "gamma_5xx_error_retrying",
                    generation_id=generation_id,
                    status_code=status_code,
                    retry_attempt=retry_count + 1,
                    retry_wait_seconds=retry_wait
                )
                await asyncio.sleep(retry_wait)
                return await self.get_generation_status(generation_id, retry_count + 1)

            # Log and raise for all other errors
            self.logger.error(
                "gamma_status_check_error",
                generation_id=generation_id,
                status_code=status_code,
                error_body=e.response.text,
                retry_count=retry_count,
                exc_info=True
            )
            raise GammaAPIError(f"Status check failed {status_code}: {e.response.text}")

        except Exception as e:
            self.logger.error(
                "gamma_status_check_failed",
                generation_id=generation_id,
                error=str(e),
                exc_info=True
            )
            raise GammaAPIError(f"Failed to check generation status: {e}")
    
    def _calculate_backoff(self, attempt: int, base: float = 2.0, max_wait: float = 30.0) -> float:
        """
        Calculate exponential backoff with optional jitter.

        Args:
            attempt: Current attempt number (0-indexed)
            base: Base interval for backoff
            max_wait: Maximum wait time

        Returns:
            Wait time in seconds
        """
        wait = min(base * (1.5 ** attempt), max_wait)
        if self.jitter:
            wait = wait * (0.5 + random.random() * 0.5)  # Add 0-50% jitter
        return wait

    async def poll_generation(
        self,
        generation_id: str,
        max_polls: Optional[int] = None,
        poll_interval: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Poll generation status until completion or failure.

        Supports:
        - Exponential backoff with jitter
        - Special handling for 429 (rate limit) - doesn't count as hard failure
        - Total timeout independent of poll count
        - Retry metrics in logs

        Args:
            generation_id: ID to poll
            max_polls: Maximum polling attempts (default: self.max_polls)
            poll_interval: Initial poll interval in seconds (default: self.poll_interval)

        Returns:
            Final generation result with gammaUrl

        Raises:
            GammaAPIError: If generation fails or times out
        """
        max_polls = max_polls or self.max_polls
        poll_interval = poll_interval or self.poll_interval

        start_time = time.time()
        self.logger.info(
            "gamma_polling_started",
            generation_id=generation_id,
            max_polls=max_polls,
            initial_interval=poll_interval,
            max_total_wait_seconds=self.max_total_wait_seconds
        )

        poll_count = 0
        rate_limit_count = 0
        retry_5xx_count = 0
        current_interval = poll_interval

        while poll_count < max_polls:
            # Check total timeout
            elapsed_time = time.time() - start_time
            if elapsed_time >= self.max_total_wait_seconds:
                self.logger.error(
                    "gamma_polling_total_timeout",
                    generation_id=generation_id,
                    elapsed_seconds=elapsed_time,
                    max_wait_seconds=self.max_total_wait_seconds
                )
                raise GammaAPIError(
                    f"Generation polling timed out after {elapsed_time:.1f}s "
                    f"(max: {self.max_total_wait_seconds}s)"
                )

            try:
                status_result = await self.get_generation_status(generation_id)
                status = status_result.get('status')

                self.logger.debug(
                    "gamma_polling_status",
                    generation_id=generation_id,
                    poll_attempt=poll_count + 1,
                    status=status,
                    elapsed_seconds=elapsed_time
                )

                if status == 'completed':
                    elapsed_total = time.time() - start_time

                    # Validate Gamma URL from API response
                    gamma_url = status_result.get('gammaUrl')
                    if gamma_url:
                        # Ensure URL is from API response, not manually constructed
                        if not gamma_url.startswith('https://gamma.app/'):
                            self.logger.warning(
                                "gamma_url_invalid_pattern",
                                generation_id=generation_id,
                                gamma_url=gamma_url
                            )
                        # Verify it's not just generation_id appended
                        if gamma_url == f"https://gamma.app/{generation_id}":
                            self.logger.warning(
                                "gamma_url_appears_constructed",
                                generation_id=generation_id,
                                gamma_url=gamma_url,
                                message="URL may be manually constructed instead of from API"
                            )
                        # Log full URL for debugging
                        self.logger.debug(
                            "gamma_url_received",
                            generation_id=generation_id,
                            full_url=gamma_url
                        )

                    self.logger.info(
                        "gamma_generation_completed",
                        generation_id=generation_id,
                        poll_attempts=poll_count + 1,
                        total_time_seconds=elapsed_total,
                        rate_limit_count=rate_limit_count,
                        retry_5xx_count=retry_5xx_count,
                        gamma_url=gamma_url,
                        credits_used=status_result.get('credits', {}).get('deducted', 0)
                    )
                    return status_result

                elif status == 'failed':
                    error_msg = status_result.get('error', 'Unknown error')
                    self.logger.error(
                        "gamma_generation_failed",
                        generation_id=generation_id,
                        error=error_msg
                    )
                    raise GammaAPIError(f"Generation failed: {error_msg}")

                elif status in ['pending', 'processing']:
                    # Continue polling with exponential backoff
                    poll_count += 1
                    if poll_count < max_polls:
                        current_interval = self._calculate_backoff(poll_count, base=poll_interval)
                        self.logger.debug(
                            "gamma_polling_wait",
                            generation_id=generation_id,
                            wait_seconds=current_interval,
                            poll_attempt=poll_count
                        )
                        await asyncio.sleep(current_interval)
                    continue

                else:
                    self.logger.warning(
                        "gamma_unknown_status",
                        generation_id=generation_id,
                        status=status
                    )
                    poll_count += 1
                    if poll_count < max_polls:
                        current_interval = self._calculate_backoff(poll_count, base=poll_interval)
                        await asyncio.sleep(current_interval)
                    continue

            except GammaAPIError as e:
                # Check if this is a 429 rate limit error
                if "429" in str(e):
                    rate_limit_count += 1
                    # Don't count as hard failure, use exponential backoff with jitter
                    backoff_wait = self._calculate_backoff(rate_limit_count, base=5.0, max_wait=30)
                    self.logger.warning(
                        "gamma_rate_limit_429",
                        generation_id=generation_id,
                        rate_limit_count=rate_limit_count,
                        backoff_seconds=backoff_wait
                    )
                    await asyncio.sleep(backoff_wait)
                    continue  # Don't increment poll_count

                # Re-raise other API errors
                raise

            except Exception as e:
                self.logger.error(
                    "gamma_polling_error",
                    generation_id=generation_id,
                    poll_attempt=poll_count + 1,
                    error=str(e),
                    exc_info=True
                )
                poll_count += 1
                if poll_count < max_polls:
                    current_interval = self._calculate_backoff(poll_count, base=poll_interval)
                    await asyncio.sleep(current_interval)
                continue

        # Max polls reached
        elapsed_total = time.time() - start_time
        self.logger.error(
            "gamma_polling_max_attempts",
            generation_id=generation_id,
            max_polls=max_polls,
            elapsed_seconds=elapsed_total,
            rate_limit_count=rate_limit_count
        )
        raise GammaAPIError(
            f"Generation polling exceeded {max_polls} attempts "
            f"(elapsed: {elapsed_total:.1f}s, rate limits: {rate_limit_count})"
        )


class GammaAPIError(Exception):
    """Exception raised for Gamma API errors."""
    pass

