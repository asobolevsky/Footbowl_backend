"""
Data models for league-related API responses
"""

from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from datetime import datetime


@dataclass
class Coverage:
    """Simplified coverage information for a season"""
    fixtures: bool
    standings: bool
    players: bool
    top_scorers: bool
    top_assists: bool
    top_cards: bool
    injuries: bool
    predictions: bool
    odds: bool
    
    @classmethod
    def from_api_data(cls, coverage_data: Dict[str, Any]) -> 'Coverage':
        """Create Coverage from API response data"""
        return cls(
            fixtures=coverage_data.get('fixtures', {}).get('events', False),
            standings=coverage_data.get('standings', False),
            players=coverage_data.get('players', False),
            top_scorers=coverage_data.get('top_scorers', False),
            top_assists=coverage_data.get('top_assists', False),
            top_cards=coverage_data.get('top_cards', False),
            injuries=coverage_data.get('injuries', False),
            predictions=coverage_data.get('predictions', False),
            odds=coverage_data.get('odds', False)
        )


@dataclass
class Season:
    """Simplified season information"""
    year: int
    start_date: str
    end_date: str
    is_current: bool
    coverage: Coverage
    
    @classmethod
    def from_api_data(cls, season_data: Dict[str, Any]) -> 'Season':
        """Create Season from API response data"""
        return cls(
            year=season_data.get('year', 0),
            start_date=season_data.get('start', ''),
            end_date=season_data.get('end', ''),
            is_current=season_data.get('current', False),
            coverage=Coverage.from_api_data(season_data.get('coverage', {}))
        )


@dataclass
class Country:
    """Simplified country information"""
    name: str
    code: str
    flag_url: str
    
    @classmethod
    def from_api_data(cls, country_data: Dict[str, Any]) -> 'Country':
        """Create Country from API response data"""
        return cls(
            name=country_data.get('name', ''),
            code=country_data.get('code', ''),
            flag_url=country_data.get('flag', '')
        )


@dataclass
class League:
    """Simplified league information"""
    id: int
    name: str
    type: str
    logo_url: str
    country: Country
    seasons: List[Season]
    
    @classmethod
    def from_api_data(cls, league_data: Dict[str, Any]) -> 'League':
        """Create League from API response data"""
        league_info = league_data.get('league', {})
        country_info = league_data.get('country', {})
        seasons_data = league_data.get('seasons', [])
        
        return cls(
            id=league_info.get('id', 0),
            name=league_info.get('name', ''),
            type=league_info.get('type', ''),
            logo_url=league_info.get('logo', ''),
            country=Country.from_api_data(country_info),
            seasons=[Season.from_api_data(season) for season in seasons_data]
        )


@dataclass
class LeagueSummary:
    """Ultra-lightweight league summary for list views"""
    id: int
    name: str
    country_name: str
    country_code: str
    logo_url: str
    current_season_year: Optional[int]
    
    @classmethod
    def from_league(cls, league: League) -> 'LeagueSummary':
        """Create LeagueSummary from League object"""
        current_season = next(
            (season for season in league.seasons if season.is_current), 
            None
        )
        
        return cls(
            id=league.id,
            name=league.name,
            country_name=league.country.name,
            country_code=league.country.code,
            logo_url=league.logo_url,
            current_season_year=current_season.year if current_season else None
        )


@dataclass
class LeagueResponse:
    """Lightweight response wrapper for leagues API"""
    leagues: List[League]
    total_count: int
    current_page: int
    total_pages: int
    
    @classmethod
    def from_api_data(cls, api_response: Dict[str, Any]) -> 'LeagueResponse':
        """Create LeagueResponse from API Football response"""
        response_data = api_response.get('response', [])
        paging_data = api_response.get('paging', {})
        
        return cls(
            leagues=[League.from_api_data(league_data) for league_data in response_data],
            total_count=api_response.get('results', 0),
            current_page=paging_data.get('current', 1),
            total_pages=paging_data.get('total', 1)
        )
    
    def to_summary_response(self) -> Dict[str, Any]:
        """Convert to ultra-lightweight summary response"""
        return {
            'leagues': [LeagueSummary.from_league(league).__dict__ for league in self.leagues],
            'total_count': self.total_count,
            'current_page': self.current_page,
            'total_pages': self.total_pages
        }
