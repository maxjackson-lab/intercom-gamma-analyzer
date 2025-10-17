"""
Gamma client for generating presentations using verified v0.2 API.
"""

import asyncio
import time
import structlog
from typing import Dict, List, Any, Optional
import httpx

from config.settings import settings

logger = structlog.get_logger()


class GammaClient:
    """Client for Gamma presentation generation using v0.2 API."""
    
    def __init__(self):
        self.api_key = settings.gamma_api_key
        self.base_url = "https://public-api.gamma.app/v0.2"
        self.timeout = 60
        self.max_polls = 30  # Max polling attempts
        self.poll_interval = 2  # Initial poll interval in seconds
        
        self.headers = {
            'X-API-KEY': self.api_key,
            'Content-Type': 'application/json'
        } if self.api_key else {}
        
        self.logger = structlog.get_logger()
        
        self.logger.info(
            "gamma_client_initialized",
            api_key_present=bool(self.api_key),
            base_url=self.base_url
        )
    
    async def test_connection(self) -> bool:
        """Test connection to Gamma API."""
        if not self.api_key:
            self.logger.warning("Gamma API key not provided, skipping connection test")
            return True
        
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
        export_as: Optional[str] = None,
        additional_instructions: Optional[str] = None,
        image_options: Optional[Dict] = None
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
        
        # Build request payload
        payload = {
            "inputText": input_text,
            "format": format,
            "numCards": num_cards,
            "textMode": text_mode
        }
        
        if export_as:
            payload["exportAs"] = export_as
        
        if additional_instructions:
            payload["additionalInstructions"] = additional_instructions[:500]
        
        if image_options:
            payload["imageOptions"] = image_options
        
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
                
                elapsed_time = (time.time() - start_time) * 1000
                
                self.logger.info(
                    "gamma_generate_request_success",
                    generation_id=generation_id,
                    response_time_ms=elapsed_time
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
    
    async def get_generation_status(self, generation_id: str) -> Dict[str, Any]:
        """
        Get the status of a generation request.
        
        Args:
            generation_id: ID returned from generate_presentation
            
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
            self.logger.error(
                "gamma_status_check_error",
                generation_id=generation_id,
                status_code=e.response.status_code,
                error_body=e.response.text,
                exc_info=True
            )
            raise GammaAPIError(f"Status check failed {e.response.status_code}: {e.response.text}")
        except Exception as e:
            self.logger.error(
                "gamma_status_check_failed",
                generation_id=generation_id,
                error=str(e),
                exc_info=True
            )
            raise GammaAPIError(f"Failed to check generation status: {e}")
    
    async def poll_generation(
        self, 
        generation_id: str, 
        max_polls: Optional[int] = None,
        poll_interval: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Poll generation status until completion or failure.
        
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
        
        self.logger.info(
            "gamma_polling_started",
            generation_id=generation_id,
            max_polls=max_polls,
            initial_interval=poll_interval
        )
        
        poll_count = 0
        current_interval = poll_interval
        
        while poll_count < max_polls:
            try:
                status_result = await self.get_generation_status(generation_id)
                status = status_result.get('status')
                
                self.logger.debug(
                    "gamma_polling_status",
                    generation_id=generation_id,
                    poll_attempt=poll_count + 1,
                    status=status
                )
                
                if status == 'completed':
                    self.logger.info(
                        "gamma_generation_completed",
                        generation_id=generation_id,
                        poll_attempts=poll_count + 1,
                        gamma_url=status_result.get('gammaUrl')
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
                        self.logger.debug(
                            "gamma_polling_wait",
                            generation_id=generation_id,
                            wait_seconds=current_interval
                        )
                        await asyncio.sleep(current_interval)
                        # Exponential backoff with max 30 seconds
                        current_interval = min(current_interval * 1.5, 30)
                    continue
                
                else:
                    self.logger.warning(
                        "gamma_unknown_status",
                        generation_id=generation_id,
                        status=status
                    )
                    poll_count += 1
                    if poll_count < max_polls:
                        await asyncio.sleep(current_interval)
                        current_interval = min(current_interval * 1.5, 30)
                    continue
                    
            except GammaAPIError:
                # Re-raise API errors
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
                    await asyncio.sleep(current_interval)
                    current_interval = min(current_interval * 1.5, 30)
                continue
        
        # Max polls reached
        self.logger.error(
            "gamma_polling_timeout",
            generation_id=generation_id,
            max_polls=max_polls
        )
        raise GammaAPIError(f"Generation polling timed out after {max_polls} attempts")


class GammaAPIError(Exception):
    """Exception raised for Gamma API errors."""
    pass

