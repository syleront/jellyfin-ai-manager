import os
import logging
from src.core.config import load_config
from src.clients.llm_client import LLMClient
from src.clients.tmdb_client import TMDBClient
from src.clients.jellyfin_client import JellyfinClient
from src.utils.fs_utils import get_failed_files, get_processed_files, mark_as_failed
from src.utils.scanner import cleanup_broken_links, scan_mixed_folder_batches
import time
from src.core.processor import MediaProcessor
from src.core.watcher import setup_watcher

def setup_logging(level_str: str):
    level = getattr(logging, level_str.upper(), logging.INFO)
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler()]
    )

def run_initial_scan(config, llm, tmdb, jellyfin, processor, logger):
    processed_count = 0
    
    logger.info("Cleaning up broken links and orphaned markers...")
    removed_links = cleanup_broken_links(config.movies_dest_path, config.series_dest_path, config.mixed_path)
    if removed_links > 0:
        logger.info(f"Removed {removed_links} broken links.")

    logger.info("Scanning for already processed files...")
    processed_files = get_processed_files(config.movies_dest_path, config.series_dest_path)
    logger.info(f"Found {len(processed_files)} already processed files.")

    logger.info("Scanning for failed files...")
    failed_files = get_failed_files(config.movies_dest_path, config.series_dest_path, config.mixed_path)
    logger.info(f"Found {len(failed_files)} failed files.")
    
    skip_files = processed_files.union(failed_files)

    logger.info(f"Starting initial scan in: {config.mixed_path}")
    
    for parent_dir, file_paths in scan_mixed_folder_batches(config.mixed_path, skip_files):
        logger.info(f"Processing folder: {parent_dir} ({len(file_paths)} files)")
        
        filenames = [os.path.basename(fp) for fp in file_paths]
        rel_folder = os.path.relpath(parent_dir, config.mixed_path)
        if rel_folder == ".":
            rel_folder = ""
            
        batch_info = llm.extract_media_info_batch(filenames, folder_context=rel_folder)
        
        if not batch_info or len(batch_info) != len(file_paths):
            logger.warning(f"Could not identify files in: {parent_dir}")
            mark_as_failed(parent_dir, config.movies_dest_path, config.mixed_path)
            continue

        for file_path, media_info in zip(file_paths, batch_info):
            media_type = media_info.get('type')
            success = False
        
            if media_type == 'movie':
                success = processor.process_movie(file_path, media_info)
            elif media_type == 'series':
                success = processor.process_series(file_path, media_info)
            
            if success:
                processed_count += 1

    if processed_count > 0:
        logger.info(f"Processed {processed_count} items. Triggering Jellyfin library refresh...")
        if config.jellyfin_movies_library_id:
            jellyfin.refresh_library(config.jellyfin_movies_library_id)
        if config.jellyfin_series_library_id:
            jellyfin.refresh_library(config.jellyfin_series_library_id)
            
    logger.info("Initial scan done!")

def main():
    config = load_config()
    setup_logging(config.log_level)
    logger = logging.getLogger("main")

    if not all([config.llm_api_key, config.tmdb_api_key, config.mixed_path, config.movies_dest_path, config.series_dest_path]):
        logger.error("Required configuration is missing in .env file!")
        return

    llm = LLMClient(config.llm_api_key, config.llm_model, config.llm_base_url)
    tmdb = TMDBClient(config.tmdb_api_key)
    jellyfin = JellyfinClient(config.jellyfin_url, config.jellyfin_api_key)
    processor = MediaProcessor(config, tmdb)

    # 1. Start watcher first to catch any changes during initial scan
    observer, handler = setup_watcher(config, llm, processor, jellyfin)

    # 2. Run initial scan
    try:
        run_initial_scan(config, llm, tmdb, jellyfin, processor, logger)
        
        # 3. Mark initial scan as complete to start processing queued events
        logger.info("Initial scan complete. Enabling real-time event processing...")
        handler.is_initial_scan_complete = True

        # Keep the main thread alive
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        observer.stop()
    
    observer.join()

if __name__ == "__main__":
    main()
