"""
Retry utilities with exponential backoff
"""

import time
import random
from typing import Callable, Any, Type, Union
from functools import wraps


class RetryConfig:
    """Configuration for retry behavior."""

    def __init__(
        self,
        max_attempts: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        backoff_factor: float = 2.0,
        jitter: bool = True,
        retry_on: Union[Type[Exception], tuple] = Exception
    ):
        """
        Initialize retry configuration.

        Args:
            max_attempts: Maximum number of retry attempts
            base_delay: Base delay between retries (seconds)
            max_delay: Maximum delay between retries (seconds)
            backoff_factor: Exponential backoff multiplier
            jitter: Add random jitter to delay
            retry_on: Exception types to retry on
        """
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.backoff_factor = backoff_factor
        self.jitter = jitter
        self.retry_on = retry_on


def retry_with_backoff(config: RetryConfig):
    """
    Decorator that implements exponential backoff retry logic.

    Args:
        config: RetryConfig instance with retry parameters

    Returns:
        Decorated function with retry logic
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            last_exception = None

            for attempt in range(config.max_attempts):
                try:
                    return func(*args, **kwargs)
                except config.retry_on as e:
                    last_exception = e

                    if attempt == config.max_attempts - 1:
                        # Last attempt failed
                        raise

                    # Calculate delay with exponential backoff
                    delay = min(
                        config.base_delay * (config.backoff_factor ** attempt),
                        config.max_delay
                    )

                    # Add jitter if enabled
                    if config.jitter:
                        delay *= (0.5 + random.random() * 0.5)  # 0.5 to 1.0 multiplier

                    time.sleep(delay)

            # This should never be reached, but just in case
            raise last_exception

        return wrapper
    return decorator


def calculate_backoff_delay(attempt: int, base_delay: float = 1.0, max_delay: float = 60.0,
                          backoff_factor: float = 2.0, jitter: bool = True) -> float:
    """
    Calculate delay for exponential backoff.

    Args:
        attempt: Current attempt number (0-based)
        base_delay: Base delay in seconds
        max_delay: Maximum delay in seconds
        backoff_factor: Exponential backoff multiplier
        jitter: Whether to add random jitter

    Returns:
        Delay in seconds
    """
    delay = min(base_delay * (backoff_factor ** attempt), max_delay)

    if jitter:
        delay *= (0.5 + random.random() * 0.5)  # 0.5 to 1.0 multiplier

    return delay