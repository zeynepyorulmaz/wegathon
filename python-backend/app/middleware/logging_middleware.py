"""
Logging middleware for FastAPI
Tracks requests, responses, and performance
"""
import time
import uuid
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
from app.core.logging import logger, set_request_context, clear_request_context


class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware to log all HTTP requests and responses"""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Generate unique request ID
        request_id = str(uuid.uuid4())
        
        # Get user/session from headers if available
        user_id = request.headers.get("X-User-ID")
        session_id = request.headers.get("X-Session-ID") or request.query_params.get("session_id")
        
        # Set context for this request
        set_request_context(
            request_id=request_id,
            user_id=user_id,
            session_id=session_id
        )
        
        # Log request
        start_time = time.time()
        logger.info(
            f"📥 {request.method} {request.url.path}",
            extra={
                "event": "request_started",
                "method": request.method,
                "path": request.url.path,
                "query_params": dict(request.query_params),
                "client_host": request.client.host if request.client else None,
                "user_agent": request.headers.get("user-agent"),
                "request_id": request_id,
                "user_id": user_id,
                "session_id": session_id,
            }
        )
        
        try:
            # Process request
            response = await call_next(request)
            
            # Calculate duration
            duration_ms = (time.time() - start_time) * 1000
            
            # Log response
            logger.info(
                f"📤 {request.method} {request.url.path} → {response.status_code} ({duration_ms:.2f}ms)",
                extra={
                    "event": "request_completed",
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                    "duration_ms": duration_ms,
                    "request_id": request_id,
                    "user_id": user_id,
                    "session_id": session_id,
                }
            )
            
            # Add request ID to response headers
            response.headers["X-Request-ID"] = request_id
            
            return response
            
        except Exception as e:
            # Calculate duration
            duration_ms = (time.time() - start_time) * 1000
            
            # Log error
            logger.error(
                f"❌ {request.method} {request.url.path} → ERROR ({duration_ms:.2f}ms): {str(e)}",
                extra={
                    "event": "request_failed",
                    "method": request.method,
                    "path": request.url.path,
                    "duration_ms": duration_ms,
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "request_id": request_id,
                    "user_id": user_id,
                    "session_id": session_id,
                }
            )
            raise
            
        finally:
            # Clear context
            clear_request_context()

