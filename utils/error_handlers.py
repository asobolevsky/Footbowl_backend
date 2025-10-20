import logging
import traceback
from flask import jsonify, request, g
from werkzeug.exceptions import HTTPException
import requests
from utils.logging_config import get_logger, log_error
from middleware.request_logger import log_security_event

# Get specialized loggers
logger = get_logger('error_handler')
security_logger = get_logger('security')

class APIError(Exception):
    """Custom API error class"""
    def __init__(self, message: str, status_code: int = 500, error_code: str = None):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        super().__init__(self.message)

def create_error_response(message: str, status_code: int, error_code: str = None, details: dict = None) -> tuple:
    """Create standardized error response with enhanced context"""
    # Get request context
    request_id = getattr(g, 'request_id', 'unknown')
    user_agent = request.headers.get('User-Agent', 'Unknown')
    remote_addr = request.remote_addr
    
    error_data = {
        'error': {
            'message': message,
            'status_code': status_code,
            'error_code': error_code or f'HTTP_{status_code}',
            'timestamp': request.environ.get('REQUEST_TIME', ''),
            'path': request.path,
            'request_id': request_id,
            'method': request.method
        }
    }
    
    if details:
        error_data['error']['details'] = details
    
    # Log error with context
    logger.error(
        f"ERROR_RESPONSE - ID: {request_id} - {request.method} {request.path} - "
        f"Status: {status_code} - Code: {error_code} - Message: {message} - "
        f"IP: {remote_addr} - UA: {user_agent[:100]}"
    )
    
    return jsonify(error_data), status_code

def handle_http_error(error: HTTPException) -> tuple:
    """Handle HTTP exceptions with enhanced logging"""
    request_id = getattr(g, 'request_id', 'unknown')
    
    # Log with context
    logger.warning(
        f"HTTP_ERROR - ID: {request_id} - {request.method} {request.path} - "
        f"Code: {error.code} - Description: {error.description} - "
        f"IP: {request.remote_addr}"
    )
    
    # Log security events for certain error codes
    if error.code in [401, 403, 429]:
        log_security_event(
            f"HTTP_{error.code}",
            f"Path: {request.path}, IP: {request.remote_addr}, UA: {request.headers.get('User-Agent', 'Unknown')[:100]}",
            severity='WARNING'
        )
    
    return create_error_response(
        message=error.description,
        status_code=error.code,
        error_code=f'HTTP_{error.code}'
    )

def handle_api_error(error: APIError) -> tuple:
    """Handle custom API errors with enhanced logging"""
    request_id = getattr(g, 'request_id', 'unknown')
    
    # Log with full context
    logger.error(
        f"API_ERROR - ID: {request_id} - {request.method} {request.path} - "
        f"Status: {error.status_code} - Code: {error.error_code} - Message: {error.message} - "
        f"IP: {request.remote_addr}"
    )
    
    # Log as security event if it's an authentication/authorization error
    if error.status_code in [401, 403]:
        log_security_event(
            f"API_{error.error_code}",
            f"Path: {request.path}, IP: {request.remote_addr}, Error: {error.message}",
            severity='WARNING'
        )
    
    return create_error_response(
        message=error.message,
        status_code=error.status_code,
        error_code=error.error_code
    )

def handle_requests_error(error: requests.exceptions.RequestException) -> tuple:
    """Handle requests library errors with enhanced logging"""
    request_id = getattr(g, 'request_id', 'unknown')
    
    if isinstance(error, requests.exceptions.ConnectionError):
        logger.error(
            f"CONNECTION_ERROR - ID: {request_id} - API Football connection failed - "
            f"Error: {str(error)} - IP: {request.remote_addr}"
        )
        return create_error_response(
            message="Unable to connect to API Football service",
            status_code=503,
            error_code='SERVICE_UNAVAILABLE',
            details={'service': 'api-football'}
        )
    
    elif isinstance(error, requests.exceptions.Timeout):
        logger.error(
            f"TIMEOUT_ERROR - ID: {request_id} - API Football request timed out - "
            f"Error: {str(error)} - IP: {request.remote_addr}"
        )
        return create_error_response(
            message="Request to API Football timed out",
            status_code=504,
            error_code='GATEWAY_TIMEOUT',
            details={'service': 'api-football'}
        )
    
    elif isinstance(error, requests.exceptions.HTTPError):
        status_code = error.response.status_code if error.response else 500
        logger.error(
            f"API_HTTP_ERROR - ID: {request_id} - API Football returned {status_code} - "
            f"Error: {str(error)} - IP: {request.remote_addr}"
        )
        
        # Log security events for authentication/authorization errors
        if status_code in [401, 403, 429]:
            log_security_event(
                f"API_FOOTBALL_{status_code}",
                f"Status: {status_code}, Error: {str(error)}, IP: {request.remote_addr}",
                severity='WARNING'
            )
        
        # Map API Football errors to appropriate responses
        if status_code == 401:
            return create_error_response(
                message="Invalid API key for API Football",
                status_code=401,
                error_code='UNAUTHORIZED',
                details={'service': 'api-football'}
            )
        elif status_code == 403:
            return create_error_response(
                message="Access forbidden - check API key permissions",
                status_code=403,
                error_code='FORBIDDEN',
                details={'service': 'api-football'}
            )
        elif status_code == 429:
            return create_error_response(
                message="Rate limit exceeded for API Football",
                status_code=429,
                error_code='RATE_LIMIT_EXCEEDED',
                details={'service': 'api-football'}
            )
        elif status_code == 404:
            return create_error_response(
                message="Resource not found in API Football",
                status_code=404,
                error_code='NOT_FOUND',
                details={'service': 'api-football'}
            )
        else:
            return create_error_response(
                message=f"API Football returned error: {status_code}",
                status_code=502,
                error_code='BAD_GATEWAY',
                details={'service': 'api-football', 'original_status': status_code}
            )
    
    else:
        logger.error(
            f"UNEXPECTED_REQUESTS_ERROR - ID: {request_id} - Unexpected API Football error - "
            f"Error: {str(error)} - Type: {type(error).__name__} - IP: {request.remote_addr}"
        )
        return create_error_response(
            message="Unexpected error communicating with API Football",
            status_code=502,
            error_code='BAD_GATEWAY',
            details={'service': 'api-football'}
        )

def handle_validation_error(error: ValueError) -> tuple:
    """Handle validation errors with enhanced logging"""
    request_id = getattr(g, 'request_id', 'unknown')
    
    logger.warning(
        f"VALIDATION_ERROR - ID: {request_id} - {request.method} {request.path} - "
        f"Error: {str(error)} - IP: {request.remote_addr}"
    )
    
    return create_error_response(
        message=str(error),
        status_code=400,
        error_code='VALIDATION_ERROR'
    )

def handle_generic_error(error: Exception) -> tuple:
    """Handle unexpected errors with comprehensive logging"""
    request_id = getattr(g, 'request_id', 'unknown')
    
    # Log the error with full context
    logger.error(
        f"UNEXPECTED_ERROR - ID: {request_id} - {request.method} {request.path} - "
        f"Error: {str(error)} - Type: {type(error).__name__} - IP: {request.remote_addr}"
    )
    
    # Log the full traceback
    logger.error(f"TRACEBACK - ID: {request_id} - {traceback.format_exc()}")
    
    # Log as security event for critical errors
    if isinstance(error, (MemoryError, SystemError, KeyboardInterrupt)):
        log_security_event(
            f"CRITICAL_ERROR_{type(error).__name__}",
            f"Error: {str(error)}, IP: {request.remote_addr}, Path: {request.path}",
            severity='CRITICAL'
        )
    
    return create_error_response(
        message="An unexpected error occurred",
        status_code=500,
        error_code='INTERNAL_SERVER_ERROR',
        details={'error_type': type(error).__name__} if logger.isEnabledFor(logging.DEBUG) else None
    )

def register_error_handlers(app):
    """Register all error handlers with the Flask app"""
    
    @app.errorhandler(400)
    def bad_request(error):
        return create_error_response(
            message="Bad request - check your parameters",
            status_code=400,
            error_code='BAD_REQUEST'
        )
    
    @app.errorhandler(401)
    def unauthorized(error):
        return create_error_response(
            message="Unauthorized - authentication required",
            status_code=401,
            error_code='UNAUTHORIZED'
        )
    
    @app.errorhandler(403)
    def forbidden(error):
        return create_error_response(
            message="Forbidden - insufficient permissions",
            status_code=403,
            error_code='FORBIDDEN'
        )
    
    @app.errorhandler(404)
    def not_found(error):
        return create_error_response(
            message="Resource not found",
            status_code=404,
            error_code='NOT_FOUND'
        )
    
    @app.errorhandler(429)
    def rate_limit_exceeded(error):
        return create_error_response(
            message="Rate limit exceeded - too many requests",
            status_code=429,
            error_code='RATE_LIMIT_EXCEEDED',
            details={'retry_after': getattr(error, 'retry_after', None)}
        )
    
    @app.errorhandler(500)
    def internal_server_error(error):
        return create_error_response(
            message="Internal server error",
            status_code=500,
            error_code='INTERNAL_SERVER_ERROR'
        )
    
    @app.errorhandler(503)
    def service_unavailable(error):
        return create_error_response(
            message="Service temporarily unavailable",
            status_code=503,
            error_code='SERVICE_UNAVAILABLE'
        )
    
    # Register custom error handlers
    app.errorhandler(APIError)(handle_api_error)
    app.errorhandler(requests.exceptions.RequestException)(handle_requests_error)
    app.errorhandler(ValueError)(handle_validation_error)
    app.errorhandler(Exception)(handle_generic_error)
    
    logger.info("Enhanced error handlers registered successfully with comprehensive logging")
