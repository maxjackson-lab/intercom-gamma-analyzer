"""
Standardized backoff utilities for API requests across all clients.

Provides exponential backoff with jitter to reduce thundering herd effects
and minimize flakiness during rate limiting or temporary failures.
"""

import random
import asyncio
from typing import Optional


def calculate_backoff_delay(
    attempt: int,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential: bool = True,
    jitter: bool = True
) -> float:
    """
    Calculate backoff delay for retry attempts.

    Args:
        attempt: Current retry attempt (0-indexed)
        base_delay: Base delay in seconds (default: 1.0)
        max_delay: Maximum delay cap in seconds (default: 60.0)
        exponential: Use exponential backoff (default: True)
        jitter: Add random jitter to prevent thundering herd (default: True)

    Returns:
        Delay in seconds
    """
    if exponential:
        delay = base_delay * (2 ** attempt)
    else:
        delay = base_delay

    # Cap at maximum delay
    delay = min(delay, max_delay)

    # Add jitter (±25% randomness)
    if jitter:
        jitter_range = delay * 0.25
        delay = delay + random.uniform(-jitter_range, jitter_range)
        delay = max(0.1, delay)  # Ensure positive, minimum 0.1s

    return delay


async def exponential_backoff_retry(
    func,
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    jitter: bool = True,
    exceptions: tuple = (Exception,)
):
    """
    Execute async function with exponential backoff retry logic.

    Args:
        func: Async function to execute
        max_retries: Maximum number of retry attempts
        base_delay: Base delay in seconds
        max_delay: Maximum delay cap in seconds
        jitter: Add random jitter to prevent thundering herd
        exceptions: Tuple of exceptions to catch and retry

    Returns:
        Result from successful function execution

    Raises:
        Last exception if all retries fail
    """
    last_exception = None

    for attempt in range(max_retries):
        try:
            return await func()
        except exceptions as e:
            last_exception = e

            if attempt == max_retries - 1:
                # Last attempt, raise the exception
                raise

            delay = calculate_backoff_delay(
                attempt=attempt,
                base_delay=base_delay,
                max_delay=max_delay,
                exponential=True,
                jitter=jitter
            )

            await asyncio.sleep(delay)

    # Should never reach here, but just in case
    if last_exception:
        raise last_exception


class BackoffConfig:
    """Configuration for backoff behavior."""

    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        jitter: bool = True
    ):
        """
        Initialize backoff configuration.

        Args:
            max_retries: Maximum number of retry attempts
            base_delay: Base delay in seconds
            max_delay: Maximum delay cap in seconds
            jitter: Add random jitter to prevent thundering herd
        """
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.jitter = jitter

    def calculate_delay(self, attempt: int) -> float:
        """Calculate delay for given attempt."""
        return calculate_backoff_delay(
            attempt=attempt,
            base_delay=self.base_delay,
            max_delay=self.max_delay,
            exponential=True,
            jitter=self.jitter
        )
