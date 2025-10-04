"""
Decorators for automatic function/method logging
"""
import time
import functools
from typing import Callable, Any
from app.core.logging import logger


def log_execution(
    level: str = "info",
    include_args: bool = True,
    include_result: bool = False,
    max_length: int = 200
):
    """
    Decorator to log function execution with timing
    
    Args:
        level: Log level (debug, info, warning, error)
        include_args: Whether to log function arguments
        include_result: Whether to log function result
        max_length: Maximum length of logged values (truncate if longer)
    
    Example:
        @log_execution(level="debug", include_args=True)
        async def my_function(param1, param2):
            return "result"
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs) -> Any:
            func_name = f"{func.__module__}.{func.__qualname__}"
            
            # Prepare arguments for logging
            args_repr = ""
            if include_args and (args or kwargs):
                args_list = [_truncate(repr(a), max_length) for a in args]
                kwargs_list = [f"{k}={_truncate(repr(v), max_length)}" for k, v in kwargs.items()]
                args_repr = ", ".join(args_list + kwargs_list)
            
            # Log function entry
            log_func = getattr(logger, level)
            log_func(
                f"→ {func_name}({args_repr})",
                extra={"event": "function_start", "function": func_name}
            )
            
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                duration_ms = (time.time() - start_time) * 1000
                
                # Log function exit
                result_repr = ""
                if include_result:
                    result_repr = f" = {_truncate(repr(result), max_length)}"
                
                log_func(
                    f"← {func_name} completed in {duration_ms:.2f}ms{result_repr}",
                    extra={
                        "event": "function_completed",
                        "function": func_name,
                        "duration_ms": duration_ms
                    }
                )
                return result
                
            except Exception as e:
                duration_ms = (time.time() - start_time) * 1000
                logger.error(
                    f"✗ {func_name} failed after {duration_ms:.2f}ms: {str(e)}",
                    extra={
                        "event": "function_failed",
                        "function": func_name,
                        "duration_ms": duration_ms,
                        "error": str(e),
                        "error_type": type(e).__name__
                    }
                )
                raise
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs) -> Any:
            func_name = f"{func.__module__}.{func.__qualname__}"
            
            # Prepare arguments for logging
            args_repr = ""
            if include_args and (args or kwargs):
                args_list = [_truncate(repr(a), max_length) for a in args]
                kwargs_list = [f"{k}={_truncate(repr(v), max_length)}" for k, v in kwargs.items()]
                args_repr = ", ".join(args_list + kwargs_list)
            
            # Log function entry
            log_func = getattr(logger, level)
            log_func(
                f"→ {func_name}({args_repr})",
                extra={"event": "function_start", "function": func_name}
            )
            
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                duration_ms = (time.time() - start_time) * 1000
                
                # Log function exit
                result_repr = ""
                if include_result:
                    result_repr = f" = {_truncate(repr(result), max_length)}"
                
                log_func(
                    f"← {func_name} completed in {duration_ms:.2f}ms{result_repr}",
                    extra={
                        "event": "function_completed",
                        "function": func_name,
                        "duration_ms": duration_ms
                    }
                )
                return result
                
            except Exception as e:
                duration_ms = (time.time() - start_time) * 1000
                logger.error(
                    f"✗ {func_name} failed after {duration_ms:.2f}ms: {str(e)}",
                    extra={
                        "event": "function_failed",
                        "function": func_name,
                        "duration_ms": duration_ms,
                        "error": str(e),
                        "error_type": type(e).__name__
                    }
                )
                raise
        
        # Return appropriate wrapper based on function type
        if functools.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


def log_api_call(service_name: str):
    """
    Decorator specifically for external API calls
    
    Args:
        service_name: Name of the external service (e.g., "MCP", "OpenAI", "Anthropic")
    
    Example:
        @log_api_call("MCP")
        async def call_mcp_api(endpoint, params):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs) -> Any:
            func_name = func.__qualname__
            
            logger.info(
                f"🌐 API Call to {service_name}: {func_name}",
                extra={
                    "event": "api_call_started",
                    "service": service_name,
                    "function": func_name
                }
            )
            
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                duration_ms = (time.time() - start_time) * 1000
                
                logger.info(
                    f"✓ {service_name} API call completed in {duration_ms:.2f}ms",
                    extra={
                        "event": "api_call_completed",
                        "service": service_name,
                        "function": func_name,
                        "duration_ms": duration_ms
                    }
                )
                return result
                
            except Exception as e:
                duration_ms = (time.time() - start_time) * 1000
                logger.error(
                    f"✗ {service_name} API call failed after {duration_ms:.2f}ms: {str(e)}",
                    extra={
                        "event": "api_call_failed",
                        "service": service_name,
                        "function": func_name,
                        "duration_ms": duration_ms,
                        "error": str(e),
                        "error_type": type(e).__name__
                    }
                )
                raise
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs) -> Any:
            func_name = func.__qualname__
            
            logger.info(
                f"🌐 API Call to {service_name}: {func_name}",
                extra={
                    "event": "api_call_started",
                    "service": service_name,
                    "function": func_name
                }
            )
            
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                duration_ms = (time.time() - start_time) * 1000
                
                logger.info(
                    f"✓ {service_name} API call completed in {duration_ms:.2f}ms",
                    extra={
                        "event": "api_call_completed",
                        "service": service_name,
                        "function": func_name,
                        "duration_ms": duration_ms
                    }
                )
                return result
                
            except Exception as e:
                duration_ms = (time.time() - start_time) * 1000
                logger.error(
                    f"✗ {service_name} API call failed after {duration_ms:.2f}ms: {str(e)}",
                    extra={
                        "event": "api_call_failed",
                        "service": service_name,
                        "function": func_name,
                        "duration_ms": duration_ms,
                        "error": str(e),
                        "error_type": type(e).__name__
                    }
                )
                raise
        
        if functools.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


def _truncate(text: str, max_length: int) -> str:
    """Truncate text to max_length"""
    if len(text) <= max_length:
        return text
    return text[:max_length - 3] + "..."

