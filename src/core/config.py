import os
from dotenv import load_dotenv
from dataclasses import dataclass

@dataclass
class Config:
    llm_api_key: str
    llm_model: str
    llm_base_url: str
    tmdb_api_key: str
    
    # Paths
    mixed_path: str
    movies_dest_path: str
    series_dest_path: str
    
    # Jellyfin
    jellyfin_url: str
    jellyfin_api_key: str
    jellyfin_movies_library_id: str
    jellyfin_series_library_id: str
    
    log_level: str

def load_config() -> Config:
    load_dotenv()
    
    return Config(
        llm_api_key=os.getenv("LLM_API_KEY", os.getenv("OPENROUTER_API_KEY", "")),
        llm_model=os.getenv("LLM_MODEL", os.getenv("OPENROUTER_MODEL", "perplexity/llama-3.1-sonar-small-128k-online")),
        llm_base_url=os.getenv("LLM_BASE_URL", os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")),
        tmdb_api_key=os.getenv("TMDB_API_KEY", ""),
        
        mixed_path=os.getenv("MIXED_PATH", ""),
        movies_dest_path=os.getenv("MOVIES_DEST_PATH", ""),
        series_dest_path=os.getenv("SERIES_DEST_PATH", ""),
        
        jellyfin_url=os.getenv("JELLYFIN_URL", ""),
        jellyfin_api_key=os.getenv("JELLYFIN_API_KEY", ""),
        jellyfin_movies_library_id=os.getenv("JELLYFIN_MOVIES_LIBRARY_ID", ""),
        jellyfin_series_library_id=os.getenv("JELLYFIN_SERIES_LIBRARY_ID", ""),
        
        log_level=os.getenv("LOG_LEVEL", "INFO")
    )
