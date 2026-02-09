import requests
import logging

logger = logging.getLogger(__name__)

class TMDBClient:
    BASE_URL = "https://api.themoviedb.org/3"

    def __init__(self, api_key: str):
        self.api_key = api_key

    def search_movie(self, title: str, year: int = None):
        """
        Searches for a movie by title and optional year.
        Returns the first result's ID or None.
        """
        params = {
            "api_key": self.api_key,
            "query": title,
            "language": "ru-RU"
        }
        if year:
            params["year"] = year

        try:
            response = requests.get(f"{self.BASE_URL}/search/movie", params=params)
            response.raise_for_status()
            results = response.json().get("results", [])
            if results:
                return results[0]["id"]
            
            if year:
                logger.info(f"No results for movie {title} ({year}), trying without year.")
                del params["year"]
                response = requests.get(f"{self.BASE_URL}/search/movie", params=params)
                response.raise_for_status()
                results = response.json().get("results", [])
                if results:
                    return results[0]["id"]
                    
            return None
        except Exception as e:
            logger.error(f"Error searching TMDB for movie {title}: {e}")
            return None

    def get_movie_details(self, movie_id: int):
        """
        Gets full movie details including credits.
        """
        params = {
            "api_key": self.api_key,
            "append_to_response": "credits",
            "language": "ru-RU"
        }
        try:
            response = requests.get(f"{self.BASE_URL}/movie/{movie_id}", params=params)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error getting TMDB movie details for ID {movie_id}: {e}")
            return None

    def search_series(self, title: str, year: int = None):
        """
        Searches for a TV series by title and optional year.
        Returns the first result's ID or None.
        """
        params = {
            "api_key": self.api_key,
            "query": title,
            "language": "ru-RU"
        }
        if year:
            params["first_air_date_year"] = year

        try:
            response = requests.get(f"{self.BASE_URL}/search/tv", params=params)
            response.raise_for_status()
            results = response.json().get("results", [])
            if results:
                return results[0]["id"]
            
            if year:
                logger.info(f"No results for series {title} ({year}), trying without year.")
                del params["first_air_date_year"]
                response = requests.get(f"{self.BASE_URL}/search/tv", params=params)
                response.raise_for_status()
                results = response.json().get("results", [])
                if results:
                    return results[0]["id"]
                    
            return None
        except Exception as e:
            logger.error(f"Error searching TMDB for series {title}: {e}")
            return None

    def get_series_details(self, series_id: int):
        """
        Gets full TV series details.
        """
        params = {
            "api_key": self.api_key,
            "append_to_response": "credits",
            "language": "ru-RU"
        }
        try:
            response = requests.get(f"{self.BASE_URL}/tv/{series_id}", params=params)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error getting TMDB series details for ID {series_id}: {e}")
            return None

    def get_episode_details(self, series_id: int, season_number: int, episode_number: int):
        """
        Gets details for a specific episode.
        """
        params = {
            "api_key": self.api_key,
            "language": "ru-RU"
        }
        try:
            response = requests.get(
                f"{self.BASE_URL}/tv/{series_id}/season/{season_number}/episode/{episode_number}",
                params=params
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error getting TMDB episode details (S{season_number}E{episode_number}) for series {series_id}: {e}")
            return None
