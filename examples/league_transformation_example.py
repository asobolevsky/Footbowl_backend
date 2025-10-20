"""
Example demonstrating the transformation from API Football response to lightweight internal models
"""

from models.league_models import LeagueResponse, LeagueSummary
from services.league_service import LeagueService

# Example API Football response (simplified)
api_response = {
    "get": "leagues",
    "parameters": {
        "type": "league",
        "current": "true"
    },
    "errors": [],
    "results": 767,
    "paging": {
        "current": 1,
        "total": 1
    },
    "response": [
        {
            "league": {
                "id": 39,
                "name": "Premier League",
                "type": "League",
                "logo": "https://media.api-sports.io/football/leagues/39.png"
            },
            "country": {
                "name": "England",
                "code": "GB-ENG",
                "flag": "https://media.api-sports.io/flags/gb-eng.svg"
            },
            "seasons": [
                {
                    "year": 2025,
                    "start": "2025-08-15",
                    "end": "2026-05-24",
                    "current": True,
                    "coverage": {
                        "fixtures": {
                            "events": True,
                            "lineups": True,
                            "statistics_fixtures": True,
                            "statistics_players": True
                        },
                        "standings": True,
                        "players": True,
                        "top_scorers": True,
                        "top_assists": True,
                        "top_cards": True,
                        "injuries": True,
                        "predictions": True,
                        "odds": True
                    }
                }
            ]
        }
    ]
}

def demonstrate_transformation():
    """Demonstrate the transformation process"""
    
    print("=== ORIGINAL API RESPONSE ===")
    print(f"Total size: {len(str(api_response))} characters")
    print(f"Results count: {api_response['results']}")
    print(f"Response items: {len(api_response['response'])}")
    
    # Transform to internal models
    print("\n=== TRANSFORMING TO INTERNAL MODELS ===")
    league_response = LeagueService.transform_api_response(api_response)
    
    print(f"Transformed leagues: {len(league_response.leagues)}")
    print(f"Total count: {league_response.total_count}")
    
    # Show full lightweight format
    print("\n=== LIGHTWEIGHT FORMAT ===")
    league = league_response.leagues[0]
    print(f"League ID: {league.id}")
    print(f"League Name: {league.name}")
    print(f"Country: {league.country.name} ({league.country.code})")
    print(f"Logo URL: {league.logo_url}")
    print(f"Seasons: {len(league.seasons)}")
    
    if league.seasons:
        season = league.seasons[0]
        print(f"  Current Season: {season.year}")
        print(f"  Start: {season.start_date}")
        print(f"  End: {season.end_date}")
        print(f"  Coverage - Fixtures: {season.coverage.fixtures}")
        print(f"  Coverage - Standings: {season.coverage.standings}")
    
    # Show ultra-lightweight summary
    print("\n=== ULTRA-LIGHTWEIGHT SUMMARY ===")
    summary_response = LeagueService.get_league_summaries(api_response)
    print(f"Summary leagues: {len(summary_response['leagues'])}")
    
    if summary_response['leagues']:
        summary = summary_response['leagues'][0]
        print(f"Summary - ID: {summary['id']}")
        print(f"Summary - Name: {summary['name']}")
        print(f"Summary - Country: {summary['country_name']} ({summary['country_code']})")
        print(f"Summary - Current Season: {summary['current_season_year']}")
    
    # Size comparison
    print("\n=== SIZE COMPARISON ===")
    original_size = len(str(api_response))
    lightweight_size = len(str(league_response.__dict__))
    summary_size = len(str(summary_response))
    
    print(f"Original API response: {original_size} characters")
    print(f"Lightweight format: {lightweight_size} characters")
    print(f"Summary format: {summary_size} characters")
    print(f"Size reduction (lightweight): {((original_size - lightweight_size) / original_size * 100):.1f}%")
    print(f"Size reduction (summary): {((original_size - summary_size) / original_size * 100):.1f}%")

if __name__ == "__main__":
    demonstrate_transformation()
