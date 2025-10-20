import logging
import time
from flask import Flask, request, jsonify
from flask_cors import CORS
from config import Config
from services.api_football_client import APIFootballClient
from services.league_service import LeagueService
from middleware.rate_limiter import setup_rate_limiter, LIVE_DATA_LIMIT, STATIC_DATA_LIMIT
from utils.error_handlers import register_error_handlers, APIError
from utils.logging_config import setup_logging, get_logger, log_request
from utils.env_logging import setup_environment_logging, configure_environment_loggers
from middleware.request_logger import setup_request_logging, log_api_endpoint

# Setup environment-specific logging
setup_environment_logging()
configure_environment_loggers()
logger = get_logger('app')

# Validate configuration
try:
    Config.validate()
except ValueError as e:
    logger.error(f"Configuration error: {e}")
    exit(1)

# Initialize Flask app
app = Flask(__name__)
app.config['JSON_SORT_KEYS'] = False

# Setup CORS
CORS(app, origins=['*'])  # Configure appropriately for production

# Setup rate limiting
limiter = setup_rate_limiter(app)

# Register error handlers
register_error_handlers(app)

# Setup enhanced request logging middleware
setup_request_logging(app)

# Initialize API client
api_client = APIFootballClient()

def get_cached_or_fetch(endpoint_name: str, api_method, params: dict, ttl: int):
    """Helper function to get data from cache or fetch from API"""
    from middleware.cache import cache_manager
    
    # Check cache first
    cache_key = cache_manager._generate_cache_key(endpoint_name, params)
    cached_data = cache_manager.get(cache_key)
    
    if cached_data is not None:
        logger.info(f"Cache hit for {endpoint_name}")
        return cached_data
    
    # Cache miss - fetch from API
    logger.info(f"Cache miss for {endpoint_name}, executing function")
    result = api_method(**params)
    
    # Cache the raw data
    if result:
        cache_manager.set(cache_key, result, ttl)
        logger.info(f"Cached result for {endpoint_name} with TTL {ttl}s")
    
    return result

# Add CORS and rate limiting headers
@app.after_request
def add_headers(response):
    # Add rate limit headers
    if hasattr(app, 'limiter'):
        rate_limit_headers = limiter.get_window_stats(request)
        if rate_limit_headers:
            response.headers.update(rate_limit_headers)
    
    # Add CORS headers
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
    
    return response

# Health check endpoint
@app.route('/health')
@log_api_endpoint('health_check')
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': time.time(),
        'version': '1.0.0',
        'services': {
            'api_football': 'connected',
            'cache': 'available' if api_client else 'unavailable'
        }
    })

# API Football proxy endpoints
# Recommended: 1 call per hour
@app.route('/api/v3/leagues')
@limiter.limit(STATIC_DATA_LIMIT)
@log_api_endpoint('get_leagues')
def get_leagues():
    """Get leagues data (raw API response)"""
    try:
        default_params = {
            'type': 'league',
            'current': 'true'
        }
        params = default_params | request.args.to_dict()
        result = get_cached_or_fetch('get_leagues', api_client.get_leagues, params, Config.CACHE_TTL_STATIC)
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error in get_leagues: {e}")
        raise APIError(f"Failed to fetch leagues: {str(e)}", 500)

# Lightweight internal API endpoints
@app.route('/api/v1/leagues')
@limiter.limit(STATIC_DATA_LIMIT)
@log_api_endpoint('get_leagues_lightweight')
def get_leagues_lightweight():
    """Get leagues data in lightweight internal format"""
    try:
        default_params = {
            'type': 'league',
            'current': 'true'
        }
        params = default_params | request.args.to_dict()
        
        # Get raw API response
        raw_response = get_cached_or_fetch('get_leagues', api_client.get_leagues, params, Config.CACHE_TTL_STATIC)
        
        # Transform to lightweight format
        transformed_response = LeagueService.transform_api_response(raw_response)
        
        # Convert to dict for JSON serialization
        return jsonify({
            'leagues': [
                {
                    'id': league.id,
                    'name': league.name,
                    'type': league.type,
                    'logo_url': league.logo_url,
                    'country': {
                        'name': league.country.name,
                        'code': league.country.code,
                        'flag_url': league.country.flag_url
                    },
                    'seasons': [
                        {
                            'year': season.year,
                            'start_date': season.start_date,
                            'end_date': season.end_date,
                            'is_current': season.is_current,
                            'coverage': {
                                'fixtures': season.coverage.fixtures,
                                'standings': season.coverage.standings,
                                'players': season.coverage.players,
                                'top_scorers': season.coverage.top_scorers,
                                'top_assists': season.coverage.top_assists,
                                'top_cards': season.coverage.top_cards,
                                'injuries': season.coverage.injuries,
                                'predictions': season.coverage.predictions,
                                'odds': season.coverage.odds
                            }
                        } for season in league.seasons
                    ]
                } for league in transformed_response.leagues
            ],
            'total_count': transformed_response.total_count,
            'current_page': transformed_response.current_page,
            'total_pages': transformed_response.total_pages
        })
    except Exception as e:
        logger.error(f"Error in get_leagues_lightweight: {e}")
        raise APIError(f"Failed to fetch leagues: {str(e)}", 500)

@app.route('/api/v1/leagues/summary')
@limiter.limit(STATIC_DATA_LIMIT)
@log_api_endpoint('get_leagues_summary')
def get_leagues_summary():
    """Get ultra-lightweight league summaries for list views"""
    try:
        default_params = {
            'type': 'league',
            'current': 'true'
        }
        params = default_params | request.args.to_dict()
        
        # Get raw API response
        raw_response = get_cached_or_fetch('get_leagues', api_client.get_leagues, params, Config.CACHE_TTL_STATIC)
        
        # Transform to summary format
        summary_response = LeagueService.get_league_summaries(raw_response)
        
        return jsonify(summary_response)
    except Exception as e:
        logger.error(f"Error in get_leagues_summary: {e}")
        raise APIError(f"Failed to fetch league summaries: {str(e)}", 500)

@app.route('/api/v3/teams')
@limiter.limit(STATIC_DATA_LIMIT)
def get_teams():
    """Get teams data"""
    try:
        params = request.args.to_dict()
        result = get_cached_or_fetch('get_teams', api_client.get_teams, params, Config.CACHE_TTL_STATIC)
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error in get_teams: {e}")
        raise APIError(f"Failed to fetch teams: {str(e)}", 500)

@app.route('/api/v3/fixtures')
@limiter.limit(LIVE_DATA_LIMIT)
@log_api_endpoint('get_fixtures')
def get_fixtures():
    """Get fixtures data"""
    try:
        params = request.args.to_dict()
        result = get_cached_or_fetch('get_fixtures', api_client.get_fixtures, params, Config.CACHE_TTL_LIVE)
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error in get_fixtures: {e}")
        raise APIError(f"Failed to fetch fixtures: {str(e)}", 500)

@app.route('/api/v3/players')
@limiter.limit(STATIC_DATA_LIMIT)
def get_players():
    """Get players data"""
    try:
        params = request.args.to_dict()
        result = get_cached_or_fetch('get_players', api_client.get_players, params, Config.CACHE_TTL_STATIC)
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error in get_players: {e}")
        raise APIError(f"Failed to fetch players: {str(e)}", 500)

@app.route('/api/v3/standings')
@limiter.limit(LIVE_DATA_LIMIT)
def get_standings():
    """Get standings data"""
    try:
        params = request.args.to_dict()
        result = get_cached_or_fetch('get_standings', api_client.get_standings, params, Config.CACHE_TTL_LIVE)
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error in get_standings: {e}")
        raise APIError(f"Failed to fetch standings: {str(e)}", 500)

@app.route('/api/v3/countries')
@limiter.limit(STATIC_DATA_LIMIT)
def get_countries():
    """Get countries data"""
    try:
        params = request.args.to_dict()
        result = get_cached_or_fetch('get_countries', api_client.get_countries, params, Config.CACHE_TTL_STATIC)
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error in get_countries: {e}")
        raise APIError(f"Failed to fetch countries: {str(e)}", 500)

@app.route('/api/v3/seasons')
@limiter.limit(STATIC_DATA_LIMIT)
def get_seasons():
    """Get seasons data"""
    try:
        params = request.args.to_dict()
        result = get_cached_or_fetch('get_seasons', api_client.get_seasons, params, Config.CACHE_TTL_STATIC)
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error in get_seasons: {e}")
        raise APIError(f"Failed to fetch seasons: {str(e)}", 500)

@app.route('/api/v3/venues')
@limiter.limit(STATIC_DATA_LIMIT)
def get_venues():
    """Get venues data"""
    try:
        params = request.args.to_dict()
        result = get_cached_or_fetch('get_venues', api_client.get_venues, params, Config.CACHE_TTL_STATIC)
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error in get_venues: {e}")
        raise APIError(f"Failed to fetch venues: {str(e)}", 500)

@app.route('/api/v3/odds')
@limiter.limit(LIVE_DATA_LIMIT)
def get_odds():
    """Get odds data"""
    try:
        params = request.args.to_dict()
        result = get_cached_or_fetch('get_odds', api_client.get_odds, params, Config.CACHE_TTL_LIVE)
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error in get_odds: {e}")
        raise APIError(f"Failed to fetch odds: {str(e)}", 500)

@app.route('/api/v3/predictions')
@limiter.limit(LIVE_DATA_LIMIT)
def get_predictions():
    """Get predictions data"""
    try:
        params = request.args.to_dict()
        result = get_cached_or_fetch('get_predictions', api_client.get_predictions, params, Config.CACHE_TTL_LIVE)
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error in get_predictions: {e}")
        raise APIError(f"Failed to fetch predictions: {str(e)}", 500)

# Generic catch-all route for any other API Football endpoints
@app.route('/api/v3/<path:endpoint>')
@limiter.limit(STATIC_DATA_LIMIT)
def get_custom_endpoint(endpoint):
    """Handle any other API Football endpoints"""
    try:
        params = request.args.to_dict()
        result = get_cached_or_fetch(f'get_custom_endpoint_{endpoint}', 
                                   lambda **kwargs: api_client.get_custom_endpoint(endpoint, **kwargs), 
                                   params, Config.CACHE_TTL_STATIC)
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error in get_custom_endpoint for {endpoint}: {e}")
        raise APIError(f"Failed to fetch {endpoint}: {str(e)}", 500)

# Root endpoint
@app.route('/')
def root():
    """Root endpoint with API information"""
    return jsonify({
        'message': 'API Football Gateway',
        'version': '1.0.0',
        'endpoints': {
            'health': '/health',
            'leagues': {
                'raw': '/api/v3/leagues',
                'lightweight': '/api/v1/leagues',
                'summary': '/api/v1/leagues/summary'
            },
            'teams': '/api/v3/teams',
            'fixtures': '/api/v3/fixtures',
            'players': '/api/v3/players',
            'standings': '/api/v3/standings',
            'countries': '/api/v3/countries',
            'seasons': '/api/v3/seasons',
            'venues': '/api/v3/venues',
            'odds': '/api/v3/odds',
            'predictions': '/api/v3/predictions'
        },
        'documentation': 'See README.md for usage examples'
    })

if __name__ == '__main__':
    logger.info("Starting API Football Gateway...")
    logger.info(f"Environment: {Config.FLASK_ENV}")
    logger.info(f"Debug mode: {Config.FLASK_DEBUG}")
    logger.info(f"Log level: {Config.LOG_LEVEL}")
    logger.info(f"Logs directory: {Config.LOGS_DIR}")
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=Config.FLASK_DEBUG
    )
