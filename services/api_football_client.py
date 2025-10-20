import requests
import logging
import time
from typing import Dict, Any, Optional
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from config import Config
from utils.logging_config import get_logger
from middleware.request_logger import log_external_api_call

# Get specialized logger
logger = get_logger('api_client')

class APIFootballClient:
    """Client for interacting with API Football service"""
    
    def __init__(self):
        self.base_url = Config.API_FOOTBALL_BASE_URL
        self.headers = {
            'x-rapidapi-key': Config.API_FOOTBALL_KEY,
            'x-rapidapi-host': Config.API_FOOTBALL_HOST,
            'Content-Type': 'application/json'
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        
        # Log client initialization
        logger.info(f"API Football client initialized - Base URL: {self.base_url}")
        logger.debug(f"Headers configured: {list(self.headers.keys())}")
    
    @retry(
        stop=stop_after_attempt(Config.MAX_RETRIES),
        wait=wait_exponential(multiplier=Config.RETRY_DELAY, min=1, max=10),
        retry=retry_if_exception_type((requests.exceptions.ConnectionError, 
                                     requests.exceptions.Timeout,
                                     requests.exceptions.HTTPError))
    )
    def _make_request(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Make HTTP request to API Football with retry logic and comprehensive logging"""
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        start_time = time.time()
        
        # Log request start
        logger.info(f"API_REQUEST_START - Endpoint: {endpoint} - URL: {url} - Params: {params}")
        
        try:
            response = self.session.get(url, params=params, timeout=30)
            response_time = (time.time() - start_time) * 1000  # Convert to milliseconds
            
            # Log response details
            logger.info(
                f"API_RESPONSE - Endpoint: {endpoint} - Status: {response.status_code} - "
                f"Time: {response_time:.2f}ms - Size: {len(response.content)} bytes"
            )
            
            response.raise_for_status()
            
            data = response.json()
            response_count = len(data.get('response', []))
            
            # Log successful response
            logger.info(
                f"API_SUCCESS - Endpoint: {endpoint} - Items: {response_count} - "
                f"Time: {response_time:.2f}ms"
            )
            
            # Log external API call for request tracking
            log_external_api_call(
                api_name='API Football',
                endpoint=endpoint,
                method='GET',
                params=params,
                response_time=response_time,
                status_code=response.status_code
            )
            
            return data
            
        except requests.exceptions.HTTPError as e:
            response_time = (time.time() - start_time) * 1000
            status_code = e.response.status_code if e.response else 0
            
            logger.error(
                f"API_HTTP_ERROR - Endpoint: {endpoint} - Status: {status_code} - "
                f"Time: {response_time:.2f}ms - Error: {str(e)}"
            )
            
            # Log external API call with error
            log_external_api_call(
                api_name='API Football',
                endpoint=endpoint,
                method='GET',
                params=params,
                response_time=response_time,
                status_code=status_code,
                error=str(e)
            )
            
            raise
            
        except requests.exceptions.ConnectionError as e:
            response_time = (time.time() - start_time) * 1000
            
            logger.error(
                f"API_CONNECTION_ERROR - Endpoint: {endpoint} - Time: {response_time:.2f}ms - "
                f"Error: {str(e)}"
            )
            
            log_external_api_call(
                api_name='API Football',
                endpoint=endpoint,
                method='GET',
                params=params,
                response_time=response_time,
                error=str(e)
            )
            
            raise
            
        except requests.exceptions.Timeout as e:
            response_time = (time.time() - start_time) * 1000
            
            logger.error(
                f"API_TIMEOUT_ERROR - Endpoint: {endpoint} - Time: {response_time:.2f}ms - "
                f"Error: {str(e)}"
            )
            
            log_external_api_call(
                api_name='API Football',
                endpoint=endpoint,
                method='GET',
                params=params,
                response_time=response_time,
                error=str(e)
            )
            
            raise
            
        except requests.exceptions.RequestException as e:
            response_time = (time.time() - start_time) * 1000
            
            logger.error(
                f"API_REQUEST_ERROR - Endpoint: {endpoint} - Time: {response_time:.2f}ms - "
                f"Error: {str(e)}"
            )
            
            log_external_api_call(
                api_name='API Football',
                endpoint=endpoint,
                method='GET',
                params=params,
                response_time=response_time,
                error=str(e)
            )
            
            raise
            
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            
            logger.error(
                f"API_UNEXPECTED_ERROR - Endpoint: {endpoint} - Time: {response_time:.2f}ms - "
                f"Error: {str(e)} - Type: {type(e).__name__}"
            )
            
            log_external_api_call(
                api_name='API Football',
                endpoint=endpoint,
                method='GET',
                params=params,
                response_time=response_time,
                error=str(e)
            )
            
            raise
    
    def get_leagues(self, **kwargs) -> Dict[str, Any]:
        """Get leagues data"""
        logger.debug(f"Getting leagues data with params: {kwargs}")
        return self._make_request('leagues', params=kwargs)
    
    def get_teams(self, **kwargs) -> Dict[str, Any]:
        """Get teams data"""
        logger.debug(f"Getting teams data with params: {kwargs}")
        return self._make_request('teams', params=kwargs)
    
    def get_fixtures(self, **kwargs) -> Dict[str, Any]:
        """Get fixtures data"""
        logger.debug(f"Getting fixtures data with params: {kwargs}")
        return self._make_request('fixtures', params=kwargs)
    
    def get_players(self, **kwargs) -> Dict[str, Any]:
        """Get players data"""
        logger.debug(f"Getting players data with params: {kwargs}")
        return self._make_request('players', params=kwargs)
    
    def get_standings(self, **kwargs) -> Dict[str, Any]:
        """Get standings data"""
        logger.debug(f"Getting standings data with params: {kwargs}")
        return self._make_request('standings', params=kwargs)
    
    def get_countries(self, **kwargs) -> Dict[str, Any]:
        """Get countries data"""
        logger.debug(f"Getting countries data with params: {kwargs}")
        return self._make_request('countries', params=kwargs)
    
    def get_seasons(self, **kwargs) -> Dict[str, Any]:
        """Get seasons data"""
        logger.debug(f"Getting seasons data with params: {kwargs}")
        return self._make_request('seasons', params=kwargs)
    
    def get_venues(self, **kwargs) -> Dict[str, Any]:
        """Get venues data"""
        logger.debug(f"Getting venues data with params: {kwargs}")
        return self._make_request('venues', params=kwargs)
    
    def get_odds(self, **kwargs) -> Dict[str, Any]:
        """Get odds data"""
        logger.debug(f"Getting odds data with params: {kwargs}")
        return self._make_request('odds', params=kwargs)
    
    def get_predictions(self, **kwargs) -> Dict[str, Any]:
        """Get predictions data"""
        logger.debug(f"Getting predictions data with params: {kwargs}")
        return self._make_request('predictions', params=kwargs)
    
    def get_custom_endpoint(self, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Get data from any custom endpoint"""
        logger.debug(f"Getting custom endpoint '{endpoint}' data with params: {kwargs}")
        return self._make_request(endpoint, params=kwargs)
