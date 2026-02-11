import os
import logging
from src.core.config import Config
from src.clients.tmdb_client import TMDBClient
from src.utils.fs_utils import (
    escape_filename, 
    create_relative_symlink, 
    mark_as_failed,
    find_external_audio_and_subtitles,
    link_external_media
)
from src.utils.nfo_generator import generate_movie_nfo, generate_series_nfo, generate_episode_nfo

logger = logging.getLogger(__name__)

class MediaProcessor:
    def __init__(self, config: Config, tmdb: TMDBClient):
        self.config = config
        self.tmdb = tmdb
        self.series_cache = {} # series_title_year -> tmdb_id

    def process_movie(self, file_path: str, media_info: dict) -> bool:
        title = media_info.get('title')
        year = media_info.get('year')
        filename = os.path.basename(file_path)
        
        logger.info(f"Processing Movie: {title} ({year})")
        
        # 1. Search TMDB
        tmdb_id = self.tmdb.search_movie(title, year)
        if not tmdb_id:
            logger.warning(f"Movie not found on TMDB: {title}")
            mark_as_failed(file_path, self.config.movies_dest_path, self.config.mixed_path)
            return False
            
        movie_data = self.tmdb.get_movie_details(tmdb_id)
        if not movie_data:
            mark_as_failed(file_path, self.config.movies_dest_path, self.config.mixed_path)
            return False
            
        # 2. Create Relative Symlink in Movies folder
        safe_title = escape_filename(title)
        dest_folder = os.path.join(self.config.movies_dest_path, f"{safe_title} ({year})")
        dest_file = os.path.join(dest_folder, f"{safe_title} ({year}){os.path.splitext(filename)[1]}")
        
        if create_relative_symlink(file_path, dest_file):
            # 3. Generate NFO
            nfo_path = os.path.splitext(dest_file)[0] + ".nfo"
            generate_movie_nfo(movie_data, nfo_path)
            
            # 4. Link external audio and subtitles
            external_files = find_external_audio_and_subtitles(file_path)
            if external_files['audio'] or external_files['subtitles']:
                linked_count = link_external_media(file_path, dest_file, external_files)
                logger.info(f"Linked {linked_count} external media files for {title}")
            else:
                logger.debug(f"No external media found for {title}")
            
            return True
        return False

    def process_series(self, file_path: str, media_info: dict) -> bool:
        series_title = media_info.get('title')
        series_year = media_info.get('year')
        season_num = media_info.get('season')
        episode_num = media_info.get('episode')
        filename = os.path.basename(file_path)

        if season_num is None or episode_num is None:
            logger.warning(f"Series detected but no S/E found: {filename}")
            mark_as_failed(file_path, self.config.series_dest_path, self.config.mixed_path)
            return False

        logger.info(f"Processing Episode: {series_title} S{season_num}E{episode_num}")

        # 1. Get Series TMDB ID
        cache_key = f"{series_title}_{series_year}"
        if cache_key not in self.series_cache:
            series_tmdb_id = self.tmdb.search_series(series_title, series_year)
            self.series_cache[cache_key] = series_tmdb_id
        else:
            series_tmdb_id = self.series_cache[cache_key]
            
        if not series_tmdb_id:
            logger.warning(f"Series not found on TMDB: {series_title}")
            mark_as_failed(file_path, self.config.series_dest_path, self.config.mixed_path)
            return False

        # 2. Create Relative Symlink in Series folder
        safe_series_title = escape_filename(series_title)
        series_folder = os.path.join(self.config.series_dest_path, f"{safe_series_title} ({series_year})")
        
        # Handle multi-season or multi-episode strings
        season_str = f"{season_num:02d}" if isinstance(season_num, int) else str(season_num)
        episode_str = f"{episode_num:02d}" if isinstance(episode_num, int) else str(episode_num)
        
        season_folder = os.path.join(series_folder, f"Season {season_num}")
        dest_file = os.path.join(season_folder, f"{safe_series_title} - S{season_str}E{episode_str}{os.path.splitext(filename)[1]}")
        
        if create_relative_symlink(file_path, dest_file):
            # 3. Generate NFOs
            # Series NFO (tvshow.nfo)
            series_nfo_path = os.path.join(series_folder, "tvshow.nfo")
            if not os.path.exists(series_nfo_path):
                series_data = self.tmdb.get_series_details(series_tmdb_id)
                if series_data:
                    generate_series_nfo(series_data, series_nfo_path)
            
            # Episode NFO
            ep_nfo_path = os.path.splitext(dest_file)[0] + ".nfo"
            ep_data = self.tmdb.get_episode_details(series_tmdb_id, season_num, episode_num)
            if ep_data:
                generate_episode_nfo(ep_data, ep_nfo_path)
                
                # 4. Link external audio and subtitles
                external_files = find_external_audio_and_subtitles(file_path)
                if external_files['audio'] or external_files['subtitles']:
                    linked_count = link_external_media(file_path, dest_file, external_files)
                    logger.info(f"Linked {linked_count} external media files for {series_title} S{season_num}E{episode_num}")
                else:
                    logger.debug(f"No external media found for {series_title} S{season_num}E{episode_num}")
                
                return True
            else:
                logger.warning(f"Episode details not found on TMDB: {series_title} S{season_num}E{episode_num}")
                mark_as_failed(file_path, self.config.series_dest_path, self.config.mixed_path)
        return False
