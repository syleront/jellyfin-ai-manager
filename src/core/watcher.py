import os
import logging
import time
import threading
import queue
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from src.core.config import Config
from src.clients.llm_client import LLMClient
from src.clients.tmdb_client import TMDBClient
from src.clients.jellyfin_client import JellyfinClient
from src.core.processor import MediaProcessor
from src.utils.scanner import cleanup_broken_links
from src.utils.fs_utils import mark_as_failed

logger = logging.getLogger(__name__)

class MediaWatcherHandler(FileSystemEventHandler):
    def __init__(self, config: Config, llm: LLMClient, processor: MediaProcessor, jellyfin: JellyfinClient):
        self.config = config
        self.llm = llm
        self.processor = processor
        self.jellyfin = jellyfin
        self.video_extensions = ('.mkv', '.mp4', '.avi', '.mov', '.m4v')
        self.event_queue = queue.Queue()
        self.is_initial_scan_complete = False
        
        # Batching logic
        self.batch_lock = threading.Lock()
        self.pending_batches = {} # folder_path -> { 'files': set(), 'timer': Timer }
        self.batch_timeout = 10.0

    def on_created(self, event):
        if event.is_directory:
            return
        if event.src_path.lower().endswith(self.video_extensions):
            logger.info(f"Event: Created -> {event.src_path}")
            self._queue_for_batching(event.src_path)

    def on_deleted(self, event):
        if event.is_directory:
            return
        logger.info(f"Event: Deleted -> {event.src_path}")
        self.event_queue.put(('deleted', event.src_path))

    def on_moved(self, event):
        if event.is_directory:
            return
        if event.dest_path.lower().endswith(self.video_extensions):
            logger.info(f"Event: Moved -> {event.dest_path}")
            self._queue_for_batching(event.dest_path)

    def _queue_for_batching(self, file_path: str):
        with self.batch_lock:
            folder_path = os.path.dirname(file_path)
            
            if folder_path not in self.pending_batches:
                self.pending_batches[folder_path] = {'files': set(), 'timer': None}
            
            batch = self.pending_batches[folder_path]
            batch['files'].add(file_path)
            
            if batch['timer']:
                batch['timer'].cancel()
            
            timer = threading.Timer(self.batch_timeout, self._trigger_batch, args=[folder_path])
            batch['timer'] = timer
            timer.start()
            logger.info(f"File queued for batching in {folder_path}. Timer reset (10s).")

    def _trigger_batch(self, folder_path: str):
        with self.batch_lock:
            if folder_path in self.pending_batches:
                batch = self.pending_batches.pop(folder_path)
                files = list(batch['files'])
                if files:
                    logger.info(f"Batch timeout reached for {folder_path}. Queuing {len(files)} files for processing.")
                    self.event_queue.put(('batch_created', (folder_path, files)))

    def process_events(self):
        """Continuously processes events from the queue."""
        while True:
            try:
                if not self.is_initial_scan_complete:
                    time.sleep(1)
                    continue

                event_type, data = self.event_queue.get(timeout=1)
                
                if event_type == 'batch_created':
                    folder_path, file_paths = data
                    self._process_batch(folder_path, file_paths)
                elif event_type == 'deleted':
                    self._handle_deletion(data)
                
                self.event_queue.task_done()
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Error processing watcher event: {e}")

    def _handle_deletion(self, file_path: str):
        logger.info(f"Handling deletion for: {file_path}")
        removed = cleanup_broken_links(self.config.movies_dest_path, self.config.series_dest_path, self.config.mixed_path)
        if removed > 0:
            logger.info(f"Cleaned up {removed} broken links after deletion.")

    def _process_batch(self, folder_path: str, file_paths: list[str]):
        # Filter out files that might have been deleted while waiting in batch
        valid_files = [fp for fp in file_paths if os.path.exists(fp)]
        if not valid_files:
            return

        logger.info(f"Processing batch of {len(valid_files)} files in: {folder_path}")
        
        filenames = [os.path.basename(fp) for fp in valid_files]
        rel_folder = os.path.relpath(folder_path, self.config.mixed_path)
        if rel_folder == ".":
            rel_folder = ""

        batch_info = self.llm.extract_media_info_batch(filenames, folder_context=rel_folder)

        if not batch_info or len(batch_info) != len(valid_files):
            logger.warning(f"Could not identify batch in: {folder_path}")
            for fp in valid_files:
                mark_as_failed(fp, self.config.movies_dest_path, self.config.mixed_path)
            return

        processed_any = False
        for file_path, media_info in zip(valid_files, batch_info):
            media_type = media_info.get('type')
            success = False

            if media_type == 'movie':
                success = self.processor.process_movie(file_path, media_info)
            elif media_type == 'series':
                success = self.processor.process_series(file_path, media_info)

            if success:
                processed_any = True

        if processed_any:
            logger.info(f"Batch processed. Triggering Jellyfin refresh...")
            if self.config.jellyfin_movies_library_id:
                self.jellyfin.refresh_library(self.config.jellyfin_movies_library_id)
            if self.config.jellyfin_series_library_id:
                self.jellyfin.refresh_library(self.config.jellyfin_series_library_id)

def setup_watcher(config: Config, llm: LLMClient, processor: MediaProcessor, jellyfin: JellyfinClient):
    """Sets up the watcher and returns the handler and observer."""
    event_handler = MediaWatcherHandler(config, llm, processor, jellyfin)
    observer = Observer()
    observer.schedule(event_handler, config.mixed_path, recursive=True)
    
    # Start the event processing thread
    processing_thread = threading.Thread(target=event_handler.process_events, daemon=True)
    processing_thread.start()
    
    observer.start()
    logger.info(f"Watcher initialized and monitoring: {config.mixed_path}")
    return observer, event_handler
