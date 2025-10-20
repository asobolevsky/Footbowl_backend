import os
import logging
from config import Config
from utils.logging_config import setup_logging, get_logger


class EnvironmentLoggingConfig:
    """Environment-specific logging configuration"""
    
    @staticmethod
    def setup_development_logging():
        """Setup logging for development environment"""
        # Override config for development
        Config.LOG_LEVEL = 'DEBUG'
        Config.LOG_FILE_ROTATE = 'size'  # Size-based rotation for development
        Config.LOG_FILE_MAX_BYTES = '500000'  # 500KB files for easier testing
        Config.LOG_FILE_BACKUP_COUNT = '5'  # Fewer backups in development
        
        # Setup logging
        setup_logging()
        
        # Get development logger
        dev_logger = get_logger('development')
        dev_logger.info("Development logging configured - DEBUG level enabled")
        
        return dev_logger
    
    @staticmethod
    def setup_production_logging():
        """Setup logging for production environment"""
        # Override config for production
        Config.LOG_LEVEL = 'INFO'
        Config.LOG_FILE_ROTATE = 'daily'  # Daily rotation for production
        Config.LOG_FILE_MAX_BYTES = '10000000'  # 10MB files
        Config.LOG_FILE_BACKUP_COUNT = '30'  # 30 days of logs
        Config.LOG_RETENTION_DAYS = 90  # Keep logs for 90 days
        
        # Setup logging
        setup_logging()
        
        # Suppress noisy loggers in production
        logging.getLogger('urllib3').setLevel(logging.WARNING)
        logging.getLogger('requests').setLevel(logging.WARNING)
        logging.getLogger('werkzeug').setLevel(logging.ERROR)
        logging.getLogger('schedule').setLevel(logging.WARNING)
        
        # Get production logger
        prod_logger = get_logger('production')
        prod_logger.info("Production logging configured - INFO level, daily rotation")
        
        return prod_logger
    
    @staticmethod
    def setup_testing_logging():
        """Setup logging for testing environment"""
        # Override config for testing
        Config.LOG_LEVEL = 'WARNING'  # Only warnings and errors
        Config.LOG_FILE_ROTATE = 'size'
        Config.LOG_FILE_MAX_BYTES = '100000'  # 100KB files
        Config.LOG_FILE_BACKUP_COUNT = '2'  # Minimal backups
        Config.LOG_RETENTION_DAYS = 1  # Keep logs for 1 day only
        
        # Setup logging
        setup_logging()
        
        # Suppress most loggers in testing
        logging.getLogger('urllib3').setLevel(logging.ERROR)
        logging.getLogger('requests').setLevel(logging.ERROR)
        logging.getLogger('werkzeug').setLevel(logging.ERROR)
        logging.getLogger('schedule').setLevel(logging.ERROR)
        
        # Get testing logger
        test_logger = get_logger('testing')
        test_logger.warning("Testing logging configured - WARNING level only")
        
        return test_logger
    
    @staticmethod
    def setup_staging_logging():
        """Setup logging for staging environment"""
        # Override config for staging
        Config.LOG_LEVEL = 'INFO'
        Config.LOG_FILE_ROTATE = 'daily'
        Config.LOG_FILE_MAX_BYTES = '5000000'  # 5MB files
        Config.LOG_FILE_BACKUP_COUNT = '14'  # 2 weeks of logs
        Config.LOG_RETENTION_DAYS = 30  # Keep logs for 30 days
        
        # Setup logging
        setup_logging()
        
        # Moderate logging for staging
        logging.getLogger('urllib3').setLevel(logging.WARNING)
        logging.getLogger('requests').setLevel(logging.WARNING)
        logging.getLogger('werkzeug').setLevel(logging.WARNING)
        
        # Get staging logger
        staging_logger = get_logger('staging')
        staging_logger.info("Staging logging configured - INFO level, daily rotation")
        
        return staging_logger


def setup_environment_logging():
    """Setup logging based on current environment"""
    env = Config.FLASK_ENV.lower()
    
    if env == 'development':
        return EnvironmentLoggingConfig.setup_development_logging()
    elif env == 'production':
        return EnvironmentLoggingConfig.setup_production_logging()
    elif env == 'testing':
        return EnvironmentLoggingConfig.setup_testing_logging()
    elif env == 'staging':
        return EnvironmentLoggingConfig.setup_staging_logging()
    else:
        # Default to development if environment is not recognized
        return EnvironmentLoggingConfig.setup_development_logging()


def get_environment_logger():
    """Get a logger configured for the current environment"""
    return get_logger(Config.FLASK_ENV.lower())


# Environment-specific log formatters
class DevelopmentFormatter(logging.Formatter):
    """Development formatter with colors and detailed info"""
    
    COLORS = {
        'DEBUG': '\033[36m',      # Cyan
        'INFO': '\033[32m',       # Green
        'WARNING': '\033[33m',    # Yellow
        'ERROR': '\033[31m',      # Red
        'CRITICAL': '\033[35m',   # Magenta
        'RESET': '\033[0m'        # Reset
    }
    
    def format(self, record):
        # Add color to level name
        if record.levelname in self.COLORS:
            record.levelname = f"{self.COLORS[record.levelname]}{record.levelname}{self.COLORS['RESET']}"
        
        # Add extra development info
        if hasattr(record, 'request_id'):
            record.msg = f"[{record.request_id}] {record.msg}"
        
        return super().format(record)


class ProductionFormatter(logging.Formatter):
    """Production formatter with structured output"""
    
    def format(self, record):
        # Create structured log entry
        log_entry = {
            'timestamp': self.formatTime(record),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }
        
        # Add request context if available
        if hasattr(record, 'request_id'):
            log_entry['request_id'] = record.request_id
        if hasattr(record, 'endpoint'):
            log_entry['endpoint'] = record.endpoint
        if hasattr(record, 'method'):
            log_entry['method'] = record.method
        if hasattr(record, 'status_code'):
            log_entry['status_code'] = record.status_code
        if hasattr(record, 'response_time'):
            log_entry['response_time'] = record.response_time
        
        # Add exception info if present
        if record.exc_info:
            log_entry['exception'] = self.formatException(record.exc_info)
        
        return str(log_entry)


class TestingFormatter(logging.Formatter):
    """Testing formatter with minimal output"""
    
    def format(self, record):
        # Only show essential information for testing
        return f"{record.levelname}: {record.getMessage()}"


# Environment-specific log levels
ENVIRONMENT_LOG_LEVELS = {
    'development': {
        'root': 'DEBUG',
        'app': 'DEBUG',
        'api_client': 'DEBUG',
        'cache': 'DEBUG',
        'rate_limiter': 'DEBUG',
        'error_handler': 'DEBUG',
        'access': 'INFO',
        'security': 'INFO'
    },
    'production': {
        'root': 'INFO',
        'app': 'INFO',
        'api_client': 'INFO',
        'cache': 'WARNING',
        'rate_limiter': 'WARNING',
        'error_handler': 'ERROR',
        'access': 'INFO',
        'security': 'WARNING'
    },
    'staging': {
        'root': 'INFO',
        'app': 'INFO',
        'api_client': 'INFO',
        'cache': 'INFO',
        'rate_limiter': 'INFO',
        'error_handler': 'WARNING',
        'access': 'INFO',
        'security': 'INFO'
    },
    'testing': {
        'root': 'WARNING',
        'app': 'WARNING',
        'api_client': 'ERROR',
        'cache': 'ERROR',
        'rate_limiter': 'ERROR',
        'error_handler': 'ERROR',
        'access': 'ERROR',
        'security': 'ERROR'
    }
}


def configure_environment_loggers():
    """Configure logger levels based on environment"""
    env = Config.FLASK_ENV.lower()
    levels = ENVIRONMENT_LOG_LEVELS.get(env, ENVIRONMENT_LOG_LEVELS['development'])
    
    for logger_name, level in levels.items():
        logger = logging.getLogger(logger_name)
        logger.setLevel(getattr(logging, level.upper()))
