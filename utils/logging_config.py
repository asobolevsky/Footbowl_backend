import os
import logging
import logging.handlers
from datetime import datetime
from config import Config


class ColoredFormatter(logging.Formatter):
    """Custom formatter with colors for console output"""
    
    # Color codes
    COLORS = {
        'DEBUG': '\033[36m',      # Cyan
        'INFO': '\033[32m',       # Green
        'WARNING': '\033[33m',    # Yellow
        'ERROR': '\033[31m',      # Red
        'CRITICAL': '\033[35m',   # Magenta
        'RESET': '\033[0m'        # Reset
    }
    
    def format(self, record):
        # Add color to the level name
        if record.levelname in self.COLORS:
            record.levelname = f"{self.COLORS[record.levelname]}{record.levelname}{self.COLORS['RESET']}"
        
        return super().format(record)


class StructuredFormatter(logging.Formatter):
    """Structured formatter for JSON-like output"""
    
    def format(self, record):
        log_entry = {
            'timestamp': datetime.fromtimestamp(record.created).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }
        
        # Add exception info if present
        if record.exc_info:
            log_entry['exception'] = self.formatException(record.exc_info)
        
        # Add extra fields if present
        if hasattr(record, 'request_id'):
            log_entry['request_id'] = record.request_id
        if hasattr(record, 'user_id'):
            log_entry['user_id'] = record.user_id
        if hasattr(record, 'endpoint'):
            log_entry['endpoint'] = record.endpoint
        if hasattr(record, 'method'):
            log_entry['method'] = record.method
        if hasattr(record, 'status_code'):
            log_entry['status_code'] = record.status_code
        if hasattr(record, 'response_time'):
            log_entry['response_time'] = record.response_time
        
        return str(log_entry)


def setup_logging():
    """Setup comprehensive logging configuration"""
    
    # Create logs directory if it doesn't exist
    os.makedirs(Config.LOGS_DIR, exist_ok=True)
    
    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, Config.LOG_LEVEL.upper()))
    
    # Clear any existing handlers
    root_logger.handlers.clear()
    
    # Create formatters
    console_formatter = ColoredFormatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt=Config.LOG_DATE_FORMAT
    )
    
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(module)s:%(funcName)s:%(lineno)d - %(message)s',
        datefmt=Config.LOG_DATE_FORMAT
    )
    
    structured_formatter = StructuredFormatter()
    
    # Console handler (always present)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG if Config.FLASK_DEBUG else logging.INFO)
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)
    
    # File handler with rotation
    log_file_path = os.path.join(Config.LOGS_DIR, Config.LOG_FILE)
    
    if Config.LOG_FILE_ROTATE.lower() == 'daily':
        file_handler = logging.handlers.TimedRotatingFileHandler(
            log_file_path,
            when='midnight',
            interval=1,
            backupCount=int(Config.LOG_FILE_BACKUP_COUNT),
            encoding=Config.LOG_FILE_ENCODING
        )
    else:  # size-based rotation
        file_handler = logging.handlers.RotatingFileHandler(
            log_file_path,
            maxBytes=int(Config.LOG_FILE_MAX_BYTES),
            backupCount=int(Config.LOG_FILE_BACKUP_COUNT),
            encoding=Config.LOG_FILE_ENCODING
        )
    
    file_handler.setLevel(getattr(logging, Config.LOG_LEVEL.upper()))
    file_handler.setFormatter(file_formatter)
    root_logger.addHandler(file_handler)
    
    # Error file handler (separate file for errors)
    error_log_path = os.path.join(Config.LOGS_DIR, 'error.log')
    error_handler = logging.handlers.RotatingFileHandler(
        error_log_path,
        maxBytes=int(Config.LOG_FILE_MAX_BYTES),
        backupCount=int(Config.LOG_FILE_BACKUP_COUNT),
        encoding=Config.LOG_FILE_ENCODING
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(file_formatter)
    root_logger.addHandler(error_handler)
    
    # Access log handler (for HTTP requests)
    access_log_path = os.path.join(Config.LOGS_DIR, 'access.log')
    access_handler = logging.handlers.RotatingFileHandler(
        access_log_path,
        maxBytes=int(Config.LOG_FILE_MAX_BYTES),
        backupCount=int(Config.LOG_FILE_BACKUP_COUNT),
        encoding=Config.LOG_FILE_ENCODING
    )
    access_handler.setLevel(logging.INFO)
    access_handler.setFormatter(file_formatter)
    
    # Create access logger
    access_logger = logging.getLogger('access')
    access_logger.setLevel(logging.INFO)
    access_logger.addHandler(access_handler)
    access_logger.propagate = False  # Don't propagate to root logger
    
    # Configure specific loggers
    configure_loggers()
    
    return root_logger


def configure_loggers():
    """Configure specific loggers for different components"""
    
    # Flask app logger
    app_logger = logging.getLogger('app')
    app_logger.setLevel(logging.INFO)
    
    # API client logger
    api_logger = logging.getLogger('api_client')
    api_logger.setLevel(logging.INFO)
    
    # Cache logger
    cache_logger = logging.getLogger('cache')
    cache_logger.setLevel(logging.INFO)
    
    # Rate limiter logger
    rate_limiter_logger = logging.getLogger('rate_limiter')
    rate_limiter_logger.setLevel(logging.INFO)
    
    # Error handler logger
    error_logger = logging.getLogger('error_handler')
    error_logger.setLevel(logging.ERROR)
    
    # Suppress some noisy loggers
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('requests').setLevel(logging.WARNING)
    logging.getLogger('werkzeug').setLevel(logging.WARNING)


def get_logger(name):
    """Get a logger instance with the given name"""
    return logging.getLogger(name)


def log_request(request, response=None, response_time=None):
    """Log HTTP request details"""
    access_logger = logging.getLogger('access')
    
    # Extract request details
    method = request.method
    path = request.path
    remote_addr = request.remote_addr
    user_agent = request.headers.get('User-Agent', 'Unknown')
    content_type = request.headers.get('Content-Type', '')
    
    # Extract response details if available
    status_code = response.status_code if response else None
    
    # Create log message
    log_data = {
        'method': method,
        'path': path,
        'remote_addr': remote_addr,
        'user_agent': user_agent,
        'content_type': content_type,
        'status_code': status_code,
        'response_time': response_time
    }
    
    # Log the request
    access_logger.info(f"Request: {method} {path} - {remote_addr} - {status_code} - {response_time}ms")


def log_api_call(endpoint, method, params=None, response_time=None, status_code=None, error=None):
    """Log API client calls"""
    api_logger = logging.getLogger('api_client')
    
    log_message = f"API Call: {method} {endpoint}"
    
    if params:
        log_message += f" - Params: {params}"
    if response_time:
        log_message += f" - Time: {response_time}ms"
    if status_code:
        log_message += f" - Status: {status_code}"
    if error:
        log_message += f" - Error: {error}"
    
    if error or (status_code and status_code >= 400):
        api_logger.error(log_message)
    else:
        api_logger.info(log_message)


def log_cache_operation(operation, key, hit=None, ttl=None):
    """Log cache operations"""
    cache_logger = logging.getLogger('cache')
    
    log_message = f"Cache {operation}: {key}"
    
    if hit is not None:
        log_message += f" - Hit: {hit}"
    if ttl:
        log_message += f" - TTL: {ttl}s"
    
    cache_logger.debug(log_message)


def log_error(error, context=None):
    """Log errors with context"""
    error_logger = logging.getLogger('error_handler')
    
    log_message = f"Error: {str(error)}"
    
    if context:
        log_message += f" - Context: {context}"
    
    error_logger.error(log_message, exc_info=True)


# Initialize logging when module is imported
if __name__ != '__main__':
    setup_logging()
