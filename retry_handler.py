#!/usr/bin/env python3
"""
Retry Handler - Decorator-based retry with exponential backoff
Provides error categories and automatic retry logic for resilient operations

Usage:
    @with_retry(max_attempts=3, base_delay=1.0)
    def my_function():
        pass
"""

import os
import sys
import time
import random
import functools
import logging
from datetime import datetime
from pathlib import Path
from enum import Enum
from typing import Callable, Any, Optional, Tuple, Type, Union

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
VAULT_PATH = Path(os.getenv("VAULT_PATH", r"F:\AI_Employee_Vault"))
LOGS_FOLDER = VAULT_PATH / "Logs"

# Ensure logs folder exists
LOGS_FOLDER.mkdir(parents=True, exist_ok=True)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOGS_FOLDER / f"retry_handler_{datetime.now().strftime('%Y-%m-%d')}.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("retry_handler")


# =============================================================================
# ERROR CATEGORIES
# =============================================================================

class BaseError(Exception):
    """Base class for all custom errors"""
    pass


class TransientError(BaseError):
    """
    Transient/temporary error that may succeed on retry
    Examples: Network timeout, temporary service unavailable, rate limit
    """
    pass


class AuthError(BaseError):
    """
    Authentication/authorization error
    Examples: Invalid credentials, token expired, permission denied
    """
    pass


class LogicError(BaseError):
    """
    Business logic error - retry unlikely to help
    Examples: Invalid input, validation failed, state conflict
    """
    pass


class DataError(BaseError):
    """
    Data-related error
    Examples: Data corruption, parsing error, missing required field
    """
    pass


class SystemError(BaseError):
    """
    System-level error
    Examples: Disk full, out of memory, file not found
    """
    pass


# Error category mapping for automatic classification
ERROR_CATEGORY_MAP = {
    # Transient errors
    "timeout": TransientError,
    "connection": TransientError,
    "network": TransientError,
    "temporary": TransientError,
    "rate limit": TransientError,
    "too many requests": TransientError,
    "service unavailable": TransientError,
    
    # Auth errors
    "authentication": AuthError,
    "authorization": AuthError,
    "unauthorized": AuthError,
    "forbidden": AuthError,
    "token": AuthError,
    "credential": AuthError,
    "permission": AuthError,
    
    # Logic errors
    "invalid": LogicError,
    "validation": LogicError,
    "conflict": LogicError,
    "constraint": LogicError,
    
    # Data errors
    "parse": DataError,
    "corrupt": DataError,
    "missing": DataError,
    "format": DataError,
    
    # System errors
    "disk": SystemError,
    "memory": SystemError,
    "file not found": SystemError,
    "permission denied": SystemError,
}


# =============================================================================
# RETRY CONFIGURATION
# =============================================================================

class RetryConfig:
    """Configuration for retry behavior"""
    
    def __init__(
        self,
        max_attempts: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        jitter: bool = True,
        jitter_factor: float = 0.5,
        retryable_errors: Optional[Tuple[Type[Exception], ...]] = None,
        non_retryable_errors: Optional[Tuple[Type[Exception], ...]] = None
    ):
        """
        Initialize retry configuration
        
        Args:
            max_attempts: Maximum number of retry attempts (default: 3)
            base_delay: Base delay between retries in seconds (default: 1.0)
            max_delay: Maximum delay between retries in seconds (default: 60.0)
            exponential_base: Base for exponential backoff (default: 2.0)
            jitter: Add randomness to delay to prevent thundering herd (default: True)
            jitter_factor: Factor for jitter calculation (default: 0.5)
            retryable_errors: Tuple of error types that should be retried
            non_retryable_errors: Tuple of error types that should NOT be retried
        """
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter
        self.jitter_factor = jitter_factor
        
        # Default retryable errors
        if retryable_errors is None:
            self.retryable_errors = (TransientError, ConnectionError, TimeoutError)
        else:
            self.retryable_errors = retryable_errors
        
        # Default non-retryable errors
        if non_retryable_errors is None:
            self.non_retryable_errors = (AuthError, LogicError, KeyboardInterrupt)
        else:
            self.non_retryable_errors = non_retryable_errors


# =============================================================================
# RETRY STATISTICS
# =============================================================================

class RetryStats:
    """Track retry statistics"""
    
    def __init__(self):
        self.total_calls = 0
        self.total_retries = 0
        self.successful_retries = 0
        self.failed_retries = 0
        self.errors_by_category = {
            "TransientError": 0,
            "AuthError": 0,
            "LogicError": 0,
            "DataError": 0,
            "SystemError": 0,
            "Other": 0
        }
    
    def record_call(self):
        self.total_calls += 1
    
    def record_retry(self, success: bool = False):
        self.total_retries += 1
        if success:
            self.successful_retries += 1
        else:
            self.failed_retries += 1
    
    def record_error(self, error: Exception):
        error_type = type(error).__name__
        if error_type in self.errors_by_category:
            self.errors_by_category[error_type] += 1
        else:
            self.errors_by_category["Other"] += 1
    
    def get_summary(self) -> dict:
        return {
            "total_calls": self.total_calls,
            "total_retries": self.total_retries,
            "successful_retries": self.successful_retries,
            "failed_retries": self.failed_retries,
            "success_rate": (self.successful_retries / max(1, self.total_retries)) * 100,
            "errors_by_category": self.errors_by_category
        }


# Global retry statistics
retry_stats = RetryStats()


# =============================================================================
# ERROR CLASSIFICATION
# =============================================================================

def classify_error(error: Exception) -> Type[BaseError]:
    """
    Classify an error into a category
    
    Args:
        error: The exception to classify
        
    Returns:
        The appropriate error category class
    """
    error_message = str(error).lower()
    error_type = type(error).__name__.lower()
    
    # Check message first
    for keyword, error_class in ERROR_CATEGORY_MAP.items():
        if keyword in error_message:
            return error_class
    
    # Check error type
    for keyword, error_class in ERROR_CATEGORY_MAP.items():
        if keyword in error_type:
            return error_class
    
    # Default classification based on exception type
    if isinstance(error, (ConnectionError, TimeoutError)):
        return TransientError
    elif isinstance(error, (PermissionError,)):
        return AuthError
    elif isinstance(error, (ValueError, TypeError)):
        return LogicError
    elif isinstance(error, (FileNotFoundError, OSError)):
        return SystemError
    
    return BaseError


def is_retryable(error: Exception, config: RetryConfig) -> bool:
    """
    Determine if an error should be retried
    
    Args:
        error: The exception to check
        config: Retry configuration
        
    Returns:
        True if the error should be retried
    """
    # Check if explicitly non-retryable
    if isinstance(error, config.non_retryable_errors):
        return False
    
    # Check if explicitly retryable
    if isinstance(error, config.retryable_errors):
        return True
    
    # Classify and determine
    error_class = classify_error(error)
    
    # AuthError and LogicError are typically not retryable
    if error_class in (AuthError, LogicError):
        return False
    
    # TransientError, DataError, SystemError may be retryable
    return True


# =============================================================================
# RETRY DECORATOR
# =============================================================================

def with_retry(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    jitter: bool = True,
    name: Optional[str] = None,
    on_retry: Optional[Callable] = None,
    on_failure: Optional[Callable] = None
):
    """
    Decorator for automatic retry with exponential backoff
    
    Args:
        max_attempts: Maximum number of attempts (default: 3)
        base_delay: Base delay in seconds (default: 1.0)
        max_delay: Maximum delay in seconds (default: 60.0)
        exponential_base: Base for exponential backoff (default: 2.0)
        jitter: Add randomness to delay (default: True)
        name: Optional name for the function (for logging)
        on_retry: Optional callback called on each retry: on_retry(attempt, error, delay)
        on_failure: Optional callback called when all retries fail: on_failure(error)
    
    Returns:
        Decorated function with retry logic
    
    Example:
        @with_retry(max_attempts=3, base_delay=1.0)
        def fetch_data():
            pass
        
        @with_retry(
            max_attempts=5,
            on_retry=lambda a, e, d: print(f"Retry {a}: {e}"),
            on_failure=lambda e: log_error(e)
        )
        def call_api():
            pass
    """
    
    def decorator(func: Callable) -> Callable:
        func_name = name or func.__name__
        
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            retry_stats.record_call()
            
            last_exception = None
            config = RetryConfig(
                max_attempts=max_attempts,
                base_delay=base_delay,
                max_delay=max_delay,
                exponential_base=exponential_base,
                jitter=jitter
            )
            
            for attempt in range(1, max_attempts + 1):
                try:
                    logger.debug(f"[{func_name}] Attempt {attempt}/{max_attempts}")
                    result = func(*args, **kwargs)
                    
                    if attempt > 1:
                        logger.info(f"[{func_name}] Success on attempt {attempt}")
                        retry_stats.record_retry(success=True)
                    
                    return result
                    
                except Exception as e:
                    last_exception = e
                    retry_stats.record_error(e)
                    
                    # Check if retryable
                    if not is_retryable(e, config):
                        logger.error(f"[{func_name}] Non-retryable error: {type(e).__name__}: {e}")
                        raise
                    
                    # Last attempt - don't retry
                    if attempt >= max_attempts:
                        logger.error(f"[{func_name}] All {max_attempts} attempts failed: {e}")
                        retry_stats.record_retry(success=False)
                        
                        if on_failure:
                            try:
                                on_failure(e)
                            except Exception as callback_error:
                                logger.error(f"on_failure callback error: {callback_error}")
                        
                        raise
                    
                    # Calculate delay with exponential backoff
                    delay = min(
                        base_delay * (exponential_base ** (attempt - 1)),
                        max_delay
                    )
                    
                    # Add jitter
                    if jitter:
                        jitter_range = delay * config.jitter_factor
                        delay = delay + random.uniform(-jitter_range, jitter_range)
                        delay = max(0.1, delay)  # Minimum 0.1 seconds
                    
                    logger.warning(
                        f"[{func_name}] Attempt {attempt} failed: {type(e).__name__}: {e}. "
                        f"Retrying in {delay:.2f}s..."
                    )
                    
                    # Call on_retry callback
                    if on_retry:
                        try:
                            on_retry(attempt, e, delay)
                        except Exception as callback_error:
                            logger.error(f"on_retry callback error: {callback_error}")
                    
                    time.sleep(delay)
            
            # Should not reach here, but just in case
            if last_exception:
                raise last_exception
        
        # Attach metadata to wrapper
        wrapper.retry_config = RetryConfig(max_attempts=max_attempts)
        wrapper.retry_stats = retry_stats
        
        return wrapper
    
    return decorator


# =============================================================================
# CONTEXT MANAGER FOR RETRY
# =============================================================================

class RetryContext:
    """
    Context manager for retry logic
    
    Usage:
        with RetryContext(max_attempts=3) as retry:
            for attempt in retry:
                try:
                    do_something()
                    break
                except Exception as e:
                    if not retry.should_retry(e):
                        raise
    """
    
    def __init__(
        self,
        max_attempts: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0
    ):
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.current_attempt = 0
        self.last_error = None
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        return False
    
    def __iter__(self):
        for i in range(self.max_attempts):
            self.current_attempt = i + 1
            yield self
    
    def should_retry(self, error: Exception) -> bool:
        """Check if should retry after this error"""
        self.last_error = error
        return is_retryable(
            error,
            RetryConfig(max_attempts=self.max_attempts, base_delay=self.base_delay)
        )
    
    def wait(self):
        """Wait before next retry with exponential backoff"""
        if self.current_attempt < self.max_attempts:
            delay = min(
                self.base_delay * (2 ** (self.current_attempt - 1)),
                self.max_delay
            )
            # Add jitter
            delay = delay + random.uniform(-delay * 0.25, delay * 0.25)
            delay = max(0.1, delay)
            time.sleep(delay)


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def get_retry_stats() -> dict:
    """Get current retry statistics"""
    return retry_stats.get_summary()


def reset_retry_stats():
    """Reset retry statistics"""
    global retry_stats
    retry_stats = RetryStats()


def quick_retry(
    func: Callable,
    *args,
    max_attempts: int = 3,
    **kwargs
) -> Any:
    """
    Quick retry wrapper for one-off operations
    
    Usage:
        result = quick_retry(some_function, arg1, arg2, max_attempts=5)
    """
    @with_retry(max_attempts=max_attempts)
    def wrapped():
        return func(*args, **kwargs)
    
    return wrapped()


# =============================================================================
# EXAMPLE USAGE AND TESTS
# =============================================================================

def _example_transient_operation():
    """Example function that may fail transiently"""
    import random
    if random.random() < 0.7:  # 70% chance of failure
        raise TransientError("Temporary failure")
    return "Success!"


def _example_auth_operation():
    """Example function that fails with auth error"""
    raise AuthError("Invalid credentials")


def test_retry_handler():
    """Test the retry handler"""
    print("=" * 60)
    print("RETRY HANDLER TEST")
    print("=" * 60)
    
    # Test 1: Successful retry after transient failures
    print("\n[Test 1] Transient error with retry...")
    call_count = [0]
    
    @with_retry(max_attempts=5, base_delay=0.1)
    def flaky_function():
        call_count[0] += 1
        if call_count[0] < 3:
            raise TransientError(f"Transient failure #{call_count[0]}")
        return f"Success after {call_count[0]} attempts"
    
    try:
        result = flaky_function()
        print(f"  Result: {result}")
        print(f"  [PASS] Retry succeeded")
    except Exception as e:
        print(f"  [FAIL] {e}")
    
    # Test 2: Non-retryable error (AuthError)
    print("\n[Test 2] Non-retryable auth error...")
    
    @with_retry(max_attempts=3, base_delay=0.1)
    def auth_function():
        raise AuthError("Invalid token")
    
    try:
        auth_function()
        print(f"  [FAIL] Should have raised AuthError")
    except AuthError:
        print(f"  [PASS] AuthError raised immediately (not retried)")
    
    # Test 3: All retries exhausted
    print("\n[Test 3] All retries exhausted...")
    attempt_count = [0]
    
    @with_retry(max_attempts=3, base_delay=0.1, on_retry=lambda a, e, d: print(f"  Retry {a}: {e}"))
    def always_fails():
        attempt_count[0] += 1
        raise TransientError("Always fails")
    
    try:
        always_fails()
        print(f"  [FAIL] Should have raised exception")
    except TransientError:
        print(f"  [PASS] Failed after {attempt_count[0]} attempts as expected")
    
    # Test 4: Callbacks
    print("\n[Test 4] Callbacks...")
    retry_events = []
    
    @with_retry(
        max_attempts=3,
        base_delay=0.1,
        on_retry=lambda a, e, d: retry_events.append(f"retry_{a}"),
        on_failure=lambda e: retry_events.append(f"failed: {e}")
    )
    def with_callbacks():
        raise TransientError("Test error")
    
    try:
        with_callbacks()
    except TransientError:
        pass
    
    print(f"  Events: {retry_events}")
    if len(retry_events) >= 3:
        print(f"  [PASS] Callbacks invoked correctly")
    else:
        print(f"  [FAIL] Expected at least 3 events")
    
    # Print summary
    print("\n" + "=" * 60)
    print("RETRY STATISTICS")
    print("=" * 60)
    stats = get_retry_stats()
    for key, value in stats.items():
        print(f"  {key}: {value}")
    
    print("\n" + "=" * 60)
    print("TEST COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    test_retry_handler()
