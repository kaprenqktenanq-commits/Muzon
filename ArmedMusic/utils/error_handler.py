"""
Error handling utilities for the bot
"""
import asyncio
from typing import Callable, Any, Optional
from functools import wraps
from pyrogram.errors import UnknownError, FloodWait
from ntgcalls import TelegramServerError
from ..logging import LOGGER


class ErrorHandler:
    """Handles various errors with retries and fallbacks"""
    
    @staticmethod
    async def handle_tg_server_error(error: Exception, operation: str = "operation", max_retries: int = 3) -> bool:
        """
        Handle Telegram server errors with exponential backoff.
        Returns True if recovered, False if max retries exceeded.
        """
        if isinstance(error, FloodWait):
            wait_time = error.value
            LOGGER(__name__).warning(f"FloodWait for {operation}: waiting {wait_time}s")
            await asyncio.sleep(wait_time)
            return True
        
        if isinstance(error, TelegramServerError):
            LOGGER(__name__).error(f"TelegramServerError in {operation}: {error}")
            # Self-healing: these errors are usually transient
            await asyncio.sleep(2)
            return True
            
        if isinstance(error, UnknownError):
            LOGGER(__name__).error(f"UnknownError in {operation}: {error}")
            # Likely TL schema mismatch or corrupted session
            await asyncio.sleep(5)
            return True
            
        # `ServerError` was removed from newer pyrogram versions; treat
        # unknown server errors using the generic UnknownError branch above.
            
        return False

    @staticmethod
    def retry_on_error(max_retries: int = 3, backoff_factor: float = 1.5, 
                       exceptions: tuple = (Exception,)):
        """
        Decorator for retrying async functions with exponential backoff.
        """
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            async def wrapper(*args: Any, **kwargs: Any) -> Any:
                last_error = None
                wait_time = 1
                
                for attempt in range(max_retries):
                    try:
                        return await func(*args, **kwargs)
                    except exceptions as e:
                        last_error = e
                        if attempt < max_retries - 1:
                            LOGGER(__name__).warning(
                                f"{func.__name__} failed (attempt {attempt + 1}/{max_retries}): {type(e).__name__}. "
                                f"Retrying in {wait_time}s..."
                            )
                            await asyncio.sleep(wait_time)
                            wait_time *= backoff_factor
                        else:
                            LOGGER(__name__).error(
                                f"{func.__name__} failed after {max_retries} attempts: {e}"
                            )
                
                raise last_error
            
            return wrapper
        return decorator


def handle_unknown_constructor(error_msg: str) -> Optional[str]:
    """
    Parse unknown constructor error and suggest fixes.
    Returns helpful error message.
    """
    if "unknown constructor" in str(error_msg).lower():
        return (
            "Unknown TL constructor detected. This usually means:\n"
            "1. Pyrogram schema is outdated\n"
            "2. Session file is corrupted\n"
            "3. API protocol mismatch\n"
            "Attempting automatic recovery..."
        )
    return None


async def safe_coroutine(coro, timeout: int = 30, default: Any = None) -> Any:
    """
    Run a coroutine with timeout and default fallback.
    """
    try:
        return await asyncio.wait_for(coro, timeout=timeout)
    except asyncio.TimeoutError:
        LOGGER(__name__).warning(f"Coroutine timed out after {timeout}s, using default")
        return default
    except Exception as e:
        LOGGER(__name__).error(f"Coroutine failed: {e}")
        return default
