"""
Service layer for league data transformation and business logic
"""

from typing import Dict, Any, List, Optional
from models.league_models import LeagueResponse, League, LeagueSummary
from utils.logging_config import get_logger

logger = get_logger('league_service')


class LeagueService:
    """Service for handling league data transformation and business logic"""
    
    @staticmethod
    def transform_api_response(api_response: Dict[str, Any]) -> LeagueResponse:
        """Transform raw API response to internal LeagueResponse model"""
        try:
            return LeagueResponse.from_api_data(api_response)
        except Exception as e:
            logger.error(f"Error transforming API response: {e}")
            raise ValueError(f"Failed to transform API response: {str(e)}")
    
    @staticmethod
    def get_league_summaries(api_response: Dict[str, Any]) -> Dict[str, Any]:
        """Get ultra-lightweight league summaries for list views"""
        try:
            league_response = LeagueService.transform_api_response(api_response)
            return league_response.to_summary_response()
        except Exception as e:
            logger.error(f"Error creating league summaries: {e}")
            raise ValueError(f"Failed to create league summaries: {str(e)}")
    
    @staticmethod
    def filter_leagues_by_country(leagues: List[League], country_code: str) -> List[League]:
        """Filter leagues by country code"""
        return [league for league in leagues if league.country.code == country_code]
    
    @staticmethod
    def filter_leagues_by_type(leagues: List[League], league_type: str) -> List[League]:
        """Filter leagues by type (League, Cup, etc.)"""
        return [league for league in leagues if league.type.lower() == league_type.lower()]
    
    @staticmethod
    def get_current_seasons_only(leagues: List[League]) -> List[League]:
        """Filter leagues to only include those with current seasons"""
        filtered_leagues = []
        for league in leagues:
            # Create a copy of the league with only current seasons
            current_seasons = [season for season in league.seasons if season.is_current]
            if current_seasons:
                # Create new league object with only current seasons
                filtered_league = League(
                    id=league.id,
                    name=league.name,
                    type=league.type,
                    logo_url=league.logo_url,
                    country=league.country,
                    seasons=current_seasons
                )
                filtered_leagues.append(filtered_league)
        return filtered_leagues
    
    @staticmethod
    def search_leagues(leagues: List[League], query: str) -> List[League]:
        """Search leagues by name or country name"""
        query_lower = query.lower()
        return [
            league for league in leagues 
            if query_lower in league.name.lower() or query_lower in league.country.name.lower()
        ]
    
    @staticmethod
    def get_league_by_id(leagues: List[League], league_id: int) -> Optional[League]:
        """Get a specific league by ID"""
        return next((league for league in leagues if league.id == league_id), None)
