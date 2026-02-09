import os
import logging

logger = logging.getLogger(__name__)

def cleanup_broken_links(movies_path: str, series_path: str, mixed_path: str = None) -> int:
    """
    Scans destination folders for broken symlinks and removes them along with their .nfo files.
    Also cleans up orphaned entries in .failed lists.
    """
    video_extensions = ('.mkv', '.mp4', '.avi', '.mov', '.m4v')
    removed_count = 0
    
    # 1. Cleanup broken symlinks and NFOs in destination folders
    for dest_root in [movies_path, series_path]:
        if not dest_root or not os.path.exists(dest_root):
            continue
            
        for root, dirs, files in os.walk(dest_root, topdown=False):
            for file in files:
                file_path = os.path.join(root, file)
                
                # Check if it's a symlink
                if os.path.islink(file_path):
                    # Check if the link is broken
                    if not os.path.exists(file_path):
                        logger.info(f"Removing broken link: {file_path}")
                        try:
                            os.remove(file_path)
                            removed_count += 1
                            
                            # Also remove corresponding .nfo if it exists
                            if file.lower().endswith(video_extensions):
                                nfo_path = os.path.splitext(file_path)[0] + ".nfo"
                                if os.path.exists(nfo_path):
                                    logger.info(f"Removing orphaned NFO: {nfo_path}")
                                    os.remove(nfo_path)
                        except Exception as e:
                            logger.error(f"Error during cleanup of {file_path}: {e}")
            
            # 2. Cleanup orphaned entries in .failed list
            failed_list_path = os.path.join(dest_root, ".failed")
            if os.path.exists(failed_list_path) and mixed_path:
                try:
                    with open(failed_list_path, 'r', encoding='utf-8') as f:
                        lines = f.readlines()
                    
                    valid_lines = []
                    for line in lines:
                        rel_path = line.strip()
                        if not rel_path: continue
                        abs_path = os.path.join(mixed_path, rel_path)
                        if os.path.exists(abs_path):
                            valid_lines.append(rel_path)
                    
                    if len(valid_lines) != len(lines):
                        logger.info(f"Cleaning up failed list in {dest_root}")
                        with open(failed_list_path, 'w', encoding='utf-8') as f:
                            for line in valid_lines:
                                f.write(line + "\n")
                except Exception as e:
                    logger.error(f"Error cleaning failed list {failed_list_path}: {e}")

            # Cleanup empty directories
            if not os.listdir(root) and root != dest_root:
                try:
                    os.rmdir(root)
                    logger.info(f"Removed empty directory: {root}")
                except Exception:
                    pass

    return removed_count

def scan_mixed_folder_batches(path: str, skip_files: set[str]):
    """Recursively scans for video files and groups them by folder, filtering out skipped ones and respecting .ignore files."""
    video_extensions = ('.mkv', '.mp4', '.avi', '.mov', '.m4v')
    for root, dirs, files in os.walk(path):
        # If .ignore file is present, skip this directory and all its subdirectories
        if '.ignore' in files:
            logger.info(f"Ignoring directory (found .ignore): {root}")
            dirs[:] = []  # Clear dirs to prevent descending into subdirectories
            continue

        # Check if current directory is marked as failed
        if os.path.abspath(root) in skip_files:
            logger.info(f"Skipping directory (marked as failed): {root}")
            dirs[:] = []
            continue

        batch = []
        for file in files:
            if file.lower().endswith(video_extensions):
                full_path = os.path.abspath(os.path.join(root, file))
                if full_path not in skip_files:
                    batch.append(full_path)
        if batch:
            yield root, batch
