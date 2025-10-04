"""
Advanced logging configuration with OpenSearch integration
"""
from loguru import logger
import sys
import os
import json
from datetime import datetime
from typing import Any, Dict, Optional
import contextvars
import httpx

# Context variables for request tracking
request_id_var = contextvars.ContextVar("request_id", default=None)
user_id_var = contextvars.ContextVar("user_id", default=None)
session_id_var = contextvars.ContextVar("session_id", default=None)


class OpenSearchHandler:
    """Handler to send logs to OpenSearch via WEGathon ingest pipeline"""
    
    def __init__(
        self,
        opensearch_url: str,
        team_name: str = "wegathon"
    ):
        self.opensearch_url = opensearch_url.rstrip('/')
        self.team_name = team_name.lower()
        self.ingest_url = f"{self.opensearch_url}/teams-ingest-pipeline/ingest"
    
    def send_log(self, record: Dict[str, Any]):
        """Send a single log record to OpenSearch via ingest pipeline (sync)"""
        try:
            import requests
            
            # Format log for WEGathon ingest pipeline
            log_entry = {
                "team": self.team_name,
                "user": record.get("user_id", "system"),
                "action": record.get("event", "log"),
                "message": record.get("message", ""),
                "level": record.get("level", "INFO"),
                "timestamp": record.get("@timestamp", datetime.utcnow().isoformat()),
                "service": "wegathon-backend",
                "module": record.get("module", ""),
                "function": record.get("function", ""),
                "request_id": record.get("request_id", ""),
                "session_id": record.get("session_id", ""),
                "extra": record.get("extra", {}),
            }
            
            # Add exception info if present
            if record.get("exception"):
                log_entry["exception"] = record["exception"]
            
            # Send as array to ingest pipeline using requests (simple, sync)
            response = requests.post(
                self.ingest_url,
                json=[log_entry],
                headers={"Content-Type": "application/json"},
                timeout=5.0
            )
            response.raise_for_status()
        except Exception as e:
            # Don't let logging errors break the application
            print(f"[OpenSearch Error] Failed to send log: {e}", file=sys.stderr)
    
    def __call__(self, message):
        """Loguru sink function"""
        record = message.record
        
        # Build structured log entry
        log_entry = {
            "@timestamp": record["time"].isoformat(),
            "level": record["level"].name,
            "logger": record["name"],
            "message": record["message"],
            "module": record["module"],
            "function": record["function"],
            "line": record["line"],
            "thread_id": record["thread"].id,
            "thread_name": record["thread"].name,
            "process_id": record["process"].id,
            "process_name": record["process"].name,
            "environment": os.getenv("ENV", "development"),
            "service": "wegathon-backend",
        }
        
        # Add context variables
        request_id = request_id_var.get()
        if request_id:
            log_entry["request_id"] = request_id
            
        user_id = user_id_var.get()
        if user_id:
            log_entry["user_id"] = user_id
            
        session_id = session_id_var.get()
        if session_id:
            log_entry["session_id"] = session_id
        
        # Add exception info if present
        if record["exception"]:
            exc_info = record["exception"]
            log_entry["exception"] = {
                "type": exc_info.type.__name__ if exc_info.type else None,
                "value": str(exc_info.value) if exc_info.value else None,
                "traceback": record["exception"].traceback if record["exception"] else None
            }
        
        # Add extra fields
        if record["extra"]:
            log_entry["extra"] = record["extra"]
        
        # Send to OpenSearch directly (requests is fast enough, no need for threading)
        self.send_log(log_entry)
        
        # Also print to stdout for local debugging (JSON format for production)
        # print(json.dumps(log_entry, default=str), file=sys.stdout)


def setup_logging():
    """Configure logging with multiple sinks"""
    
    # Load .env file explicitly
    from dotenv import load_dotenv
    from pathlib import Path
    
    # Find .env file (current dir or parent dirs)
    env_path = Path(__file__).parent.parent.parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)
    
    # Remove default logger
    logger.remove()
    
    # Get configuration from environment
    log_level = os.getenv("LOG_LEVEL", "INFO")
    enable_opensearch = os.getenv("ENABLE_OPENSEARCH_LOGGING", "false").lower() == "true"
    opensearch_url = os.getenv("OPENSEARCH_URL", "")
    team_name = os.getenv("TEAM_NAME", "wegathon")
    
    # Console logging (structured JSON in production, pretty in development)
    env = os.getenv("ENV", "development")
    
    if env == "development":
        # Pretty console output for development
        logger.add(
            sys.stdout,
            format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | <level>{message}</level>",
            level=log_level,
            colorize=True,
        )
    else:
        # JSON output for production
        logger.add(
            sys.stdout,
            format="{message}",
            level=log_level,
            serialize=True,  # Output as JSON
        )
    
    # OpenSearch logging (if enabled)
    if enable_opensearch and opensearch_url:
        try:
            opensearch_handler = OpenSearchHandler(
                opensearch_url=opensearch_url,
                team_name=team_name,
            )
            logger.add(
                opensearch_handler,
                level=log_level,
                format="{message}",
            )
            logger.info(f"✅ OpenSearch logging enabled: {opensearch_url} (team: {team_name})")
        except Exception as e:
            logger.warning(f"⚠️  Failed to setup OpenSearch logging: {e}")
    
    # File logging (optional, for local debugging)
    if os.getenv("ENABLE_FILE_LOGGING", "false").lower() == "true":
        log_dir = os.getenv("LOG_DIR", "logs")
        os.makedirs(log_dir, exist_ok=True)
        
        # Regular logs
        logger.add(
            f"{log_dir}/wegathon_{{time:YYYY-MM-DD}}.log",
            rotation="00:00",
            retention="30 days",
            level=log_level,
            format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} | {message}",
        )
        
        # Error logs (separate file)
        logger.add(
            f"{log_dir}/wegathon_errors_{{time:YYYY-MM-DD}}.log",
            rotation="00:00",
            retention="90 days",
            level="ERROR",
            format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} | {message}",
        )
    
    return logger


# Initialize logging
setup_logging()


# Helper functions for structured logging
def log_with_context(
    level: str,
    message: str,
    request_id: Optional[str] = None,
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
    **extra
):
    """Log with additional context"""
    log_func = getattr(logger, level.lower(), logger.info)
    log_func(message, **extra)


def set_request_context(request_id: str = None, user_id: str = None, session_id: str = None):
    """Set context variables for the current request"""
    if request_id:
        request_id_var.set(request_id)
    if user_id:
        user_id_var.set(user_id)
    if session_id:
        session_id_var.set(session_id)


def clear_request_context():
    """Clear context variables"""
    request_id_var.set(None)
    user_id_var.set(None)
    session_id_var.set(None)


__all__ = [
    "logger",
    "log_with_context",
    "set_request_context",
    "clear_request_context",
    "request_id_var",
    "user_id_var",
    "session_id_var",
]
