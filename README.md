# API Football Gateway

A production-ready Flask API gateway that serves as an intermediary for the API Football service, providing request proxying, authentication management, caching, rate limiting, error handling, and retry logic.

## Features

- **Authentication**: Secure API key management via environment variables
- **Caching**: Redis-based caching to reduce API calls and improve response times
- **Rate Limiting**: Protect against abuse and manage API quota
- **Retry Logic**: Automatic retries with exponential backoff for transient failures
- **Error Handling**: Comprehensive error handling with meaningful responses
- **CORS Support**: Enable frontend applications to consume the API
- **Logging**: Detailed logging for monitoring and debugging

## Quick Start

### 1. Environment Setup

```sh
# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configuration

```sh
# Copy environment template
cp .env.example .env

# Edit .env with your API Football key
# API_FOOTBALL_KEY=your_api_football_key_here
```

### 3. Start Redis (Optional but recommended)

```sh
# Using Docker
docker run -d -p 6379:6379 redis:alpine

# Or install locally
# macOS: brew install redis && brew services start redis
# Ubuntu: sudo apt install redis-server && sudo systemctl start redis
```

### 4. Run the Application

```sh
# Development mode
python app.py

# Or using Flask CLI
# (5000 is userd by AirPlay on Mac)
flask run --host=0.0.0.0 --port=5001
```

The server will start on `http://localhost:5001`

## Environment Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `API_FOOTBALL_KEY` | Your API Football API key | - | Yes |
| `API_FOOTBALL_HOST` | API Football host | `api-football-v1.p.rapidapi.com` | No |
| `REDIS_URL` | Redis connection string | `redis://localhost:6379/0` | No |
| `RATE_LIMIT` | Requests per minute limit | `100` | No |
| `FLASK_ENV` | Flask environment | `development` | No |
| `FLASK_DEBUG` | Enable debug mode | `True` | No |

## API Endpoints

### Health Check
```http
GET /health
```

### Available Endpoints

| Endpoint | Description | Rate Limit | Cache TTL |
|----------|-------------|------------|-----------|
| `GET /api/v3/leagues` | Get leagues data | 100/min | 24 hours |
| `GET /api/v3/teams` | Get teams data | 100/min | 24 hours |
| `GET /api/v3/fixtures` | Get fixtures data | 30/min | 5 minutes |
| `GET /api/v3/players` | Get players data | 100/min | 24 hours |
| `GET /api/v3/standings` | Get standings data | 30/min | 5 minutes |
| `GET /api/v3/countries` | Get countries data | 100/min | 24 hours |
| `GET /api/v3/seasons` | Get seasons data | 100/min | 24 hours |
| `GET /api/v3/venues` | Get venues data | 100/min | 24 hours |
| `GET /api/v3/odds` | Get odds data | 30/min | 5 minutes |
| `GET /api/v3/predictions` | Get predictions data | 30/min | 5 minutes |
| `GET /api/v3/<endpoint>` | Any other API Football endpoint | 100/min | 24 hours |

## Usage Examples

### Get Premier League Teams
```bash
curl "http://localhost:5000/api/v3/teams?league=39&season=2023"
```

### Get Today's Fixtures
```bash
curl "http://localhost:5000/api/v3/fixtures?date=$(date +%Y-%m-%d)"
```

### Get League Standings
```bash
curl "http://localhost:5000/api/v3/standings?league=39&season=2023"
```

### Get Player Statistics
```bash
curl "http://localhost:5000/api/v3/players?league=39&season=2023&page=1"
```

## Rate Limiting

The gateway implements rate limiting to protect the API Football service:

- **Static Data**: 100 requests per minute (leagues, teams, players, etc.)
- **Live Data**: 30 requests per minute (fixtures, standings, odds, etc.)

Rate limit headers are included in responses:
- `X-RateLimit-Limit`: Maximum requests allowed
- `X-RateLimit-Remaining`: Remaining requests in current window
- `X-RateLimit-Reset`: Time when the rate limit resets

## Caching

The gateway uses Redis for caching responses:

- **Static Data**: Cached for 24 hours (leagues, teams, players, etc.)
- **Live Data**: Cached for 5 minutes (fixtures, standings, odds, etc.)

Cache keys are generated based on endpoint and parameters to ensure uniqueness.

## Error Handling

The gateway provides comprehensive error handling:

- **400 Bad Request**: Invalid parameters
- **401 Unauthorized**: Invalid API key
- **403 Forbidden**: Insufficient permissions
- **404 Not Found**: Resource not found
- **429 Too Many Requests**: Rate limit exceeded
- **500 Internal Server Error**: Unexpected server error
- **502 Bad Gateway**: API Football service error
- **503 Service Unavailable**: Service temporarily unavailable
- **504 Gateway Timeout**: Request timeout

All errors return structured JSON responses with error details.

## Development

### Project Structure
```
backend/
├── app.py                          # Main Flask application
├── config.py                       # Configuration management
├── requirements.txt                # Python dependencies
├── .env.example                    # Environment template
├── .env                           # Local secrets (gitignored)
├── services/
│   └── api_football_client.py     # API Football wrapper
├── middleware/
│   ├── cache.py                   # Caching logic
│   └── rate_limiter.py            # Rate limiting setup
└── utils/
    └── error_handlers.py          # Error handling utilities
```

### Adding New Endpoints

To add support for new API Football endpoints:

1. Add the method to `APIFootballClient` in `services/api_football_client.py`
2. Add the route to `app.py` with appropriate rate limiting and caching
3. Update this README with the new endpoint documentation

## Logging System

The API Football Gateway includes a comprehensive logging system with the following features:

### Log Files

Logs are stored in the `logs/` directory with the following structure:

- **`app.log`** - Main application logs (INFO, WARNING, ERROR, CRITICAL)
- **`access.log`** - HTTP request/response logs with performance metrics
- **`error.log`** - Error-specific logs (ERROR and CRITICAL levels only)

### Log Levels

The logging system supports different levels based on environment:

- **Development**: DEBUG level with detailed information
- **Production**: INFO level with essential information
- **Staging**: INFO level with moderate detail
- **Testing**: WARNING level only (minimal logging)

### Log Rotation

Logs are automatically rotated based on configuration:

- **Daily rotation** in production/staging
- **Size-based rotation** in development (500KB files)
- **Compression** of old log files
- **Retention** period configurable (default: 30 days)

### Request Tracking

Every request is assigned a unique Request ID for easy tracing:

- Request ID is included in all log entries
- Response headers include `X-Request-ID` for debugging
- Complete request lifecycle can be traced through logs

### Log Management

Use the log management utility for maintenance:

```bash
# View log statistics
python utils/log_manager.py stats

# Compress old logs
python utils/log_manager.py compress

# Clean up old logs
python utils/log_manager.py cleanup

# Run full maintenance
python utils/log_manager.py maintenance
```

### Environment Configuration

Set these environment variables to configure logging:

```bash
# Log directory (default: logs)
LOGS_DIR=logs

# Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
LOG_LEVEL=INFO

# Log file settings
LOG_FILE=app.log
LOG_FILE_MAX_BYTES=1000000
LOG_FILE_BACKUP_COUNT=10
LOG_FILE_ROTATE=daily

# Log retention
LOG_RETENTION_DAYS=30
LOG_COMPRESSION_ENABLED=True
```

### Log Analysis

Logs include structured information for easy analysis:

- **Request timing**: Response times in milliseconds
- **Cache performance**: Hit/miss ratios and TTL information
- **API calls**: External API Football requests with timing
- **Error context**: Full stack traces with request context
- **Security events**: Authentication failures, rate limiting

### Monitoring Integration

The logging system is designed for easy integration with monitoring tools:

- **Structured JSON output** available for production
- **Request ID correlation** across all log entries
- **Performance metrics** embedded in log messages
- **Error tracking** with full context

## Production Deployment

For production deployment:

1. Set `FLASK_ENV=production` and `FLASK_DEBUG=False`
2. Configure proper CORS origins instead of `*`
3. Use a production WSGI server like Gunicorn
4. Set up proper Redis configuration
5. Configure logging and monitoring
6. Set up SSL/TLS termination
7. Configure log rotation and retention policies

## License

This project is licensed under the MIT License.
