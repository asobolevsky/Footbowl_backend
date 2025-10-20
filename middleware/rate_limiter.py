import logging
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask import Flask
from config import Config

logger = logging.getLogger(__name__)

def setup_rate_limiter(app: Flask) -> Limiter:
    """Setup and configure Flask-Limiter for the application"""
    
    try:
        # Initialize limiter with Redis backend
        limiter = Limiter(
            app=app,
            key_func=get_remote_address,
            storage_uri=Config.REDIS_URL,
            default_limits=[f"{Config.RATE_LIMIT} per minute"],
            headers_enabled=True
        )
        
        logger.info(f"Rate limiter configured with {Config.RATE_LIMIT} requests per minute")
        return limiter
        
    except Exception as e:
        logger.warning(f"Failed to setup Redis-based rate limiter: {e}")
        logger.info("Falling back to in-memory rate limiter")
        
        # Fallback to in-memory storage
        limiter = Limiter(
            app=app,
            key_func=get_remote_address,
            default_limits=[f"{Config.RATE_LIMIT} per minute"],
            headers_enabled=True
        )
        
        return limiter

def get_rate_limit_headers(limiter: Limiter, request) -> dict:
    """Get rate limit headers for the current request"""
    try:
        # Get current rate limit info
        current_limit = limiter.get_window_stats(request)
        
        headers = {
            'X-RateLimit-Limit': str(Config.RATE_LIMIT),
            'X-RateLimit-Remaining': str(max(0, Config.RATE_LIMIT - current_limit.hits)),
            'X-RateLimit-Reset': str(current_limit.reset_time),
        }
        
        return headers
        
    except Exception as e:
        logger.error(f"Error getting rate limit headers: {e}")
        return {}

# Custom rate limit decorators for specific endpoints
def custom_rate_limit(limit: str):
    """Custom rate limit decorator for specific endpoints"""
    def decorator(func):
        func._rate_limit = limit
        return func
    return decorator

# Predefined rate limits for different endpoint types
LIVE_DATA_LIMIT = "30 per minute"  # More restrictive for live data
STATIC_DATA_LIMIT = "100 per minute"  # Standard limit for static data
HEAVY_ENDPOINT_LIMIT = "10 per minute"  # For computationally expensive endpoints
