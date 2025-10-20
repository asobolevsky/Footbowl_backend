import time
import uuid
import logging
from flask import request, g
from functools import wraps
from utils.logging_config import get_logger, log_request


def generate_request_id():
    """Generate a unique request ID"""
    return str(uuid.uuid4())[:8]


def setup_request_logging(app):
    """Setup comprehensive request logging middleware"""
    
    # Get the access logger
    access_logger = get_logger('access')
    
    @app.before_request
    def before_request():
        """Log request start and add request context"""
        # Generate unique request ID
        request_id = generate_request_id()
        g.request_id = request_id
        
        # Store request start time
        g.request_start_time = time.time()
        
        # Extract request details
        method = request.method
        path = request.path
        remote_addr = request.remote_addr
        user_agent = request.headers.get('User-Agent', 'Unknown')
        content_type = request.headers.get('Content-Type', '')
        content_length = request.headers.get('Content-Length', '0')
        
        # Get query parameters (limit to avoid log spam)
        query_params = dict(request.args)
        if len(str(query_params)) > 200:  # Truncate long query strings
            query_params = {k: str(v)[:50] + '...' if len(str(v)) > 50 else v 
                          for k, v in query_params.items()}
        
        # Log request start
        access_logger.info(
            f"REQUEST_START - ID: {request_id} - {method} {path} - "
            f"IP: {remote_addr} - UA: {user_agent[:100]} - "
            f"Content-Type: {content_type} - Content-Length: {content_length} - "
            f"Query: {query_params}"
        )
        
        # Add request ID to response headers (for debugging)
        request.environ['REQUEST_ID'] = request_id
    
    @app.after_request
    def after_request(response):
        """Log request completion with performance metrics"""
        # Calculate response time
        if hasattr(g, 'request_start_time'):
            response_time = (time.time() - g.request_start_time) * 1000  # Convert to milliseconds
        else:
            response_time = 0
        
        # Get request details
        request_id = getattr(g, 'request_id', 'unknown')
        method = request.method
        path = request.path
        status_code = response.status_code
        content_length = response.content_length or 0
        
        # Determine log level based on status code
        if status_code >= 500:
            log_level = logging.ERROR
        elif status_code >= 400:
            log_level = logging.WARNING
        else:
            log_level = logging.INFO
        
        # Log request completion
        access_logger.log(
            log_level,
            f"REQUEST_COMPLETE - ID: {request_id} - {method} {path} - "
            f"Status: {status_code} - Time: {response_time:.2f}ms - "
            f"Size: {content_length} bytes"
        )
        
        # Add request ID to response headers
        response.headers['X-Request-ID'] = request_id
        
        # Log slow requests (over 1 second)
        if response_time > 1000:
            access_logger.warning(
                f"SLOW_REQUEST - ID: {request_id} - {method} {path} - "
                f"Time: {response_time:.2f}ms - Status: {status_code}"
            )
        
        return response
    
    @app.errorhandler(Exception)
    def log_exception(error):
        """Log unhandled exceptions with request context"""
        request_id = getattr(g, 'request_id', 'unknown')
        access_logger.error(
            f"REQUEST_ERROR - ID: {request_id} - {request.method} {request.path} - "
            f"Error: {str(error)} - Type: {type(error).__name__}",
            exc_info=True
        )
        raise error  # Re-raise the exception


def log_api_endpoint(endpoint_name):
    """Decorator to log API endpoint calls with additional context"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            request_id = getattr(g, 'request_id', 'unknown')
            logger = get_logger('app')
            
            # Log endpoint entry
            logger.info(f"ENDPOINT_ENTRY - ID: {request_id} - {endpoint_name} - Args: {args} - Kwargs: {kwargs}")
            
            try:
                result = f(*args, **kwargs)
                logger.info(f"ENDPOINT_SUCCESS - ID: {request_id} - {endpoint_name}")
                return result
            except Exception as e:
                logger.error(f"ENDPOINT_ERROR - ID: {request_id} - {endpoint_name} - Error: {str(e)}")
                raise
        
        return decorated_function
    return decorator


def log_external_api_call(api_name, endpoint, method='GET', params=None, response_time=None, status_code=None, error=None):
    """Log external API calls with detailed information"""
    api_logger = get_logger('api_client')
    request_id = getattr(g, 'request_id', 'unknown')
    
    # Build log message
    log_parts = [
        f"EXTERNAL_API - ID: {request_id}",
        f"API: {api_name}",
        f"Endpoint: {endpoint}",
        f"Method: {method}"
    ]
    
    if params:
        # Truncate long parameter values
        truncated_params = {k: str(v)[:100] + '...' if len(str(v)) > 100 else v 
                          for k, v in params.items()}
        log_parts.append(f"Params: {truncated_params}")
    
    if response_time is not None:
        log_parts.append(f"Time: {response_time:.2f}ms")
    
    if status_code:
        log_parts.append(f"Status: {status_code}")
    
    if error:
        log_parts.append(f"Error: {str(error)}")
    
    log_message = " - ".join(log_parts)
    
    # Log at appropriate level
    if error or (status_code and status_code >= 400):
        api_logger.error(log_message)
    else:
        api_logger.info(log_message)


def log_cache_operation(operation, key, hit=None, ttl=None, size=None):
    """Log cache operations with performance metrics"""
    cache_logger = get_logger('cache')
    request_id = getattr(g, 'request_id', 'unknown')
    
    log_parts = [
        f"CACHE_OP - ID: {request_id}",
        f"Operation: {operation}",
        f"Key: {key}"
    ]
    
    if hit is not None:
        log_parts.append(f"Hit: {hit}")
    
    if ttl is not None:
        log_parts.append(f"TTL: {ttl}s")
    
    if size is not None:
        log_parts.append(f"Size: {size} bytes")
    
    log_message = " - ".join(log_parts)
    cache_logger.debug(log_message)


def log_rate_limit_event(limit_type, remaining, reset_time, endpoint=None):
    """Log rate limiting events"""
    rate_limiter_logger = get_logger('rate_limiter')
    request_id = getattr(g, 'request_id', 'unknown')
    
    log_message = (
        f"RATE_LIMIT - ID: {request_id} - Type: {limit_type} - "
        f"Remaining: {remaining} - Reset: {reset_time}"
    )
    
    if endpoint:
        log_message += f" - Endpoint: {endpoint}"
    
    rate_limiter_logger.warning(log_message)


def log_security_event(event_type, details, severity='INFO'):
    """Log security-related events"""
    security_logger = get_logger('security')
    request_id = getattr(g, 'request_id', 'unknown')
    
    log_message = f"SECURITY - ID: {request_id} - Event: {event_type} - Details: {details}"
    
    # Log at appropriate level based on severity
    if severity.upper() == 'CRITICAL':
        security_logger.critical(log_message)
    elif severity.upper() == 'WARNING':
        security_logger.warning(log_message)
    else:
        security_logger.info(log_message)
