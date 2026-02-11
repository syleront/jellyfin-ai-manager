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
        self.video_extensions = ('.mkv', '.mp4', '.avi', '.mov', '.m4v', '.m2ts')
        self.audio_extensions = ('.mka', '.mp3', '.aac', '.ac3', '.dts', '.flac')
        self.subtitle_extensions = ('.ass', '.srt', '.ssa', '.sub', '.vtt')
        self.external_media_extensions = self.audio_extensions + self.subtitle_extensions
        self.event_queue = queue.Queue()
        self.is_initial_scan_complete = False
        
        # Batching logic
        self.batch_lock = threading.Lock()
        self.pending_batches = {} # folder_path -> { 'files': set(), 'timer': Timer }
        self.batch_timeout = 10.0

    def on_created(self, event):
        if event.is_directory:
            return
        file_lower = event.src_path.lower()
        if file_lower.endswith(self.video_extensions):
            logger.info(f"Event: Created -> {event.src_path}")
            self._queue_for_batching(event.src_path)
        elif file_lower.endswith(self.external_media_extensions):
            # External media added - trigger re-linking for associated video
            logger.info(f"Event: Created external media -> {event.src_path}")
            self.event_queue.put(('external_media_added', event.src_path))

    def on_deleted(self, event):
        if event.is_directory:
            return
        file_lower = event.src_path.lower()
        logger.info(f"Event: Deleted -> {event.src_path}")
        # Trigger cleanup for any deleted file (video, audio, or subtitle)
        self.event_queue.put(('deleted', event.src_path))

    def on_moved(self, event):
        if event.is_directory:
            return
        dest_lower = event.dest_path.lower()
        if dest_lower.endswith(self.video_extensions):
            logger.info(f"Event: Moved -> {event.dest_path}")
            self._queue_for_batching(event.dest_path)
        elif dest_lower.endswith(self.external_media_extensions):
            logger.info(f"Event: Moved external media -> {event.dest_path}")
            # Treat move as delete + create
            self.event_queue.put(('deleted', event.src_path))
            self.event_queue.put(('external_media_added', event.dest_path))

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
                elif event_type == 'external_media_added':
                    self._handle_external_media_added(data)
                
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

    def _handle_external_media_added(self, file_path: str):
        """Handle addition of external media (audio/subtitle) by re-linking to existing video."""
        logger.info(f"Handling external media addition: {file_path}")
        
        # Find the matching video file
        video_file = self._find_matching_video(file_path)
        if not video_file:
            logger.warning(f"No matching video found for external media: {file_path}")
            return
        
        logger.info(f"Found matching video: {video_file}")
        
        # Determine if it's a movie or series and re-process
        # We need to find the existing symlink in dest folders
        from src.utils.fs_utils import find_external_audio_and_subtitles, link_external_media
        
        dest_video = self._find_dest_symlink(video_file)
        if not dest_video:
            logger.warning(f"No destination symlink found for video: {video_file}")
            return
        
        logger.info(f"Re-linking external media for: {os.path.basename(dest_video)}")
        
        # Find all external media for this video and re-link
        external_files = find_external_audio_and_subtitles(video_file)
        linked_count = link_external_media(video_file, dest_video, external_files)
        
        if linked_count > 0:
            logger.info(f"Linked {linked_count} external media file(s)")
            # Trigger Jellyfin refresh
            if dest_video.startswith(self.config.movies_dest_path) and self.config.jellyfin_movies_library_id:
                self.jellyfin.refresh_library(self.config.jellyfin_movies_library_id)
            elif dest_video.startswith(self.config.series_dest_path) and self.config.jellyfin_series_library_id:
                self.jellyfin.refresh_library(self.config.jellyfin_series_library_id)
    
    def _find_matching_video(self, external_media_path: str) -> str:
        """Find the video file that this external media belongs to."""
        media_dir = os.path.dirname(external_media_path)
        media_filename = os.path.basename(external_media_path)
        media_name_no_ext = os.path.splitext(media_filename)[0]
        
        # Search upwards in the directory tree until we find a video file
        # that matches this external media filename
        current_dir = media_dir
        max_depth = 5  # Prevent infinite loops
        depth = 0
        
        while depth < max_depth and current_dir.startswith(self.config.mixed_path):
            # Check current directory and all subdirectories for video files
            try:
                for root, dirs, files in os.walk(current_dir):
                    for file in files:
                        if file.lower().endswith(self.video_extensions):
                            video_name_no_ext = os.path.splitext(file)[0]
                            # Check if external media filename starts with video filename
                            if media_filename.startswith(video_name_no_ext):
                                logger.debug(f"Found matching video: {file} for {media_filename}")
                                return os.path.join(root, file)
            except Exception as e:
                logger.error(f"Error searching for video in {current_dir}: {e}")
            
            # Move up one directory
            parent = os.path.dirname(current_dir)
            if parent == current_dir:  # Reached root
                break
            current_dir = parent
            depth += 1
        
        return None
    
    def _find_dest_symlink(self, video_src_path: str) -> str:
        """Find the destination symlink for a given source video file."""
        for dest_root in [self.config.movies_dest_path, self.config.series_dest_path]:
            if not dest_root or not os.path.exists(dest_root):
                continue
            
            for root, dirs, files in os.walk(dest_root):
                for file in files:
                    if file.lower().endswith(self.video_extensions):
                        dest_path = os.path.join(root, file)
                        if os.path.islink(dest_path):
                            try:
                                # Resolve symlink
                                link_target = os.readlink(dest_path)
                                if not os.path.isabs(link_target):
                                    link_target = os.path.normpath(os.path.join(root, link_target))
                                
                                # Compare absolute paths
                                if os.path.abspath(link_target) == os.path.abspath(video_src_path):
                                    return dest_path
                            except Exception:
                                pass
        
        return None

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
