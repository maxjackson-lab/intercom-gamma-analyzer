"""Generic async retry utilities."""

from __future__ import annotations

import asyncio
import functools
import random
from typing import Any, Awaitable, Callable, Iterable, Tuple, Type


def async_retry(
    *,
    retries: int = 3,
    base_delay: float = 0.5,
    backoff_factor: float = 2.0,
    jitter: float = 0.5,
    retry_exceptions: Iterable[Type[BaseException]] | Tuple[Type[BaseException], ...] = (Exception,),
) -> Callable[[Callable[..., Awaitable[Any]]], Callable[..., Awaitable[Any]]]:
    """Retry decorator for async callables with exponential backoff and jitter."""

    if isinstance(retry_exceptions, Iterable) and not isinstance(retry_exceptions, tuple):
        retry_exceptions = tuple(retry_exceptions)

    def decorator(func: Callable[..., Awaitable[Any]]) -> Callable[..., Awaitable[Any]]:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            delay = base_delay
            attempt = 1
            while True:
                try:
                    return await func(*args, **kwargs)
                except retry_exceptions as exc:  # type: ignore[arg-type]
                    if attempt >= retries:
                        raise
                    await asyncio.sleep(delay + random.uniform(0, jitter))
                    delay *= backoff_factor
                    attempt += 1

        return wrapper

    return decorator

