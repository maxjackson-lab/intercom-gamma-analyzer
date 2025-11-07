"""
Circuit breaker pattern for handling repeated failures.

Prevents cascading failures by temporarily stopping requests to failing services.
"""

import time
import logging
from enum import Enum
from typing import Optional, Callable, Any
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"      # Normal operation, requests allowed
    OPEN = "open"          # Failing, requests blocked
    HALF_OPEN = "half_open"  # Testing if service recovered


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker behavior"""
    failure_threshold: int = 5  # Failures before opening circuit
    success_threshold: int = 2  # Successes in half-open to close circuit
    timeout_seconds: float = 60.0  # Time before transitioning OPEN -> HALF_OPEN
    expected_exceptions: tuple = (Exception,)  # Exceptions that count as failures


@dataclass
class CircuitBreakerStats:
    """Statistics tracked by circuit breaker"""
    failures: int = 0
    successes: int = 0
    last_failure_time: Optional[float] = None
    last_success_time: Optional[float] = None
    state_transitions: list = field(default_factory=list)


class CircuitBreaker:
    """
    Circuit breaker for handling repeated failures.
    
    Prevents cascading failures by temporarily blocking requests to failing services.
    Automatically recovers when service appears healthy again.
    
    Example:
        ```python
        breaker = CircuitBreaker(
            name="intercom_api",
            config=CircuitBreakerConfig(failure_threshold=5, timeout_seconds=60)
        )
        
        try:
            result = await breaker.call_async(intercom_service.fetch_conversations, start_date, end_date)
        except CircuitBreakerOpenError:
            # Service is down, use fallback or return cached data
            return cached_data
        ```
    """
    
    def __init__(
        self,
        name: str,
        config: Optional[CircuitBreakerConfig] = None
    ):
        """
        Initialize circuit breaker.
        
        Args:
            name: Name of the circuit breaker (for logging)
            config: Configuration for circuit breaker behavior
        """
        self.name = name
        self.config = config or CircuitBreakerConfig()
        self.state = CircuitState.CLOSED
        self.stats = CircuitBreakerStats()
        self.logger = logging.getLogger(f"{__name__}.{name}")
    
    def _transition_to(self, new_state: CircuitState, reason: str):
        """Transition to new state with logging"""
        if self.state != new_state:
            old_state = self.state
            self.state = new_state
            self.stats.state_transitions.append({
                'from': old_state.value,
                'to': new_state.value,
                'reason': reason,
                'timestamp': time.time()
            })
            self.logger.info(
                f"Circuit breaker {self.name} transitioned: {old_state.value} -> {new_state.value} ({reason})"
            )
    
    def _should_attempt_half_open(self) -> bool:
        """Check if enough time has passed to attempt half-open state"""
        if self.state != CircuitState.OPEN:
            return False
        
        if self.stats.last_failure_time is None:
            return True
        
        elapsed = time.time() - self.stats.last_failure_time
        return elapsed >= self.config.timeout_seconds
    
    async def call_async(
        self,
        func: Callable,
        *args,
        **kwargs
    ) -> Any:
        """
        Execute async function with circuit breaker protection.
        
        Args:
            func: Async function to execute
            *args: Positional arguments for function
            **kwargs: Keyword arguments for function
            
        Returns:
            Result from function execution
            
        Raises:
            CircuitBreakerOpenError: If circuit is open (service is failing)
            Original exception: If function fails and circuit is closed/half-open
        """
        # Check if circuit is open
        if self.state == CircuitState.OPEN:
            if self._should_attempt_half_open():
                self._transition_to(CircuitState.HALF_OPEN, "Timeout expired, testing recovery")
            else:
                raise CircuitBreakerOpenError(
                    f"Circuit breaker {self.name} is OPEN. "
                    f"Service has failed {self.stats.failures} times. "
                    f"Will retry after {self.config.timeout_seconds}s"
                )
        
        # Attempt to call function
        try:
            result = await func(*args, **kwargs)
            
            # Success - update stats
            self.stats.successes += 1
            self.stats.last_success_time = time.time()
            
            # Reset failure count on success
            if self.state == CircuitState.CLOSED:
                self.stats.failures = 0
            elif self.state == CircuitState.HALF_OPEN:
                # If we've had enough successes in half-open, close the circuit
                if self.stats.successes >= self.config.success_threshold:
                    self._transition_to(CircuitState.CLOSED, f"{self.stats.successes} successes in half-open")
                    self.stats.failures = 0
                    self.stats.successes = 0
            
            return result
            
        except self.config.expected_exceptions as e:
            # Failure - update stats
            self.stats.failures += 1
            self.stats.last_failure_time = time.time()
            self.stats.successes = 0  # Reset success count on failure
            
            self.logger.warning(
                f"Circuit breaker {self.name} recorded failure ({self.stats.failures}/{self.config.failure_threshold}): {e}"
            )
            
            # Check if we should open the circuit
            if self.state == CircuitState.CLOSED:
                if self.stats.failures >= self.config.failure_threshold:
                    self._transition_to(
                        CircuitState.OPEN,
                        f"{self.stats.failures} failures reached threshold {self.config.failure_threshold}"
                    )
            elif self.state == CircuitState.HALF_OPEN:
                # Failed again in half-open, go back to open
                self._transition_to(CircuitState.OPEN, "Failed again in half-open state")
            
            # Re-raise the original exception
            raise
    
    def reset(self):
        """Manually reset circuit breaker to closed state"""
        self._transition_to(CircuitState.CLOSED, "Manual reset")
        self.stats = CircuitBreakerStats()
        self.logger.info(f"Circuit breaker {self.name} manually reset")
    
    def get_stats(self) -> dict:
        """Get current circuit breaker statistics"""
        return {
            'name': self.name,
            'state': self.state.value,
            'failures': self.stats.failures,
            'successes': self.stats.successes,
            'last_failure_time': self.stats.last_failure_time,
            'last_success_time': self.stats.last_success_time,
            'state_transitions': len(self.stats.state_transitions)
        }


class CircuitBreakerOpenError(Exception):
    """Raised when circuit breaker is open and request is blocked"""
    pass

