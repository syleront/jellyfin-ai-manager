import os
import logging

logger = logging.getLogger(__name__)

def cleanup_broken_links(movies_path: str, series_path: str, mixed_path: str = None) -> int:
    """
    Scans destination folders for broken symlinks and removes them along with their .nfo files.
    Also removes orphaned audio/subtitle files and cleans up orphaned entries in .failed lists.
    """
    video_extensions = ('.mkv', '.mp4', '.avi', '.mov', '.m4v', '.m2ts')
    audio_extensions = ('.mka', '.mp3', '.aac', '.ac3', '.dts', '.flac')
    subtitle_extensions = ('.ass', '.srt', '.ssa', '.sub', '.vtt')
    extra_extensions = audio_extensions + subtitle_extensions
    removed_count = 0
    
    # 1. Cleanup broken symlinks and NFOs in destination folders
    for dest_root in [movies_path, series_path]:
        if not dest_root or not os.path.exists(dest_root):
            continue
            
        # Pass 1: Collect valid video files to find orphaned external media
        video_files_in_dest = set()
        for root, dirs, files in os.walk(dest_root):
            for file in files:
                if file.lower().endswith(video_extensions):
                    path = os.path.join(root, file)
                    if os.path.exists(path): # Works for healthy symlinks and regular files
                        video_files_in_dest.add(os.path.splitext(file)[0])

        # Pass 2: Actually remove broken/orphaned files
        for root, dirs, files in os.walk(dest_root, topdown=False):
            for file in files:
                file_path = os.path.join(root, file)
                file_lower = file.lower()
                
                # Check for broken symlinks (ANY media type)
                if os.path.islink(file_path) and not os.path.exists(file_path):
                    logger.info(f"Removing broken link: {file_path}")
                    try:
                        os.remove(file_path)
                        removed_count += 1
                        
                        # Also remove corresponding .nfo if it was a video file
                        if file_lower.endswith(video_extensions):
                            nfo_path = os.path.splitext(file_path)[0] + ".nfo"
                            if os.path.exists(nfo_path):
                                logger.info(f"Removing orphaned NFO: {nfo_path}")
                                os.remove(nfo_path)
                    except Exception as e:
                        logger.error(f"Error during cleanup of broken link {file_path}: {e}")
                    continue

                # Check for orphaned audio/subtitle files (symlinks or healthy files)
                if file_lower.endswith(extra_extensions):
                    base_name = os.path.splitext(file)[0]
                    # Check if matching video file exists
                    video_found = False
                    for video_base in video_files_in_dest:
                        if base_name == video_base or base_name.startswith(video_base):
                            video_found = True
                            break
                    
                    if not video_found:
                        logger.info(f"Removing orphaned external media: {file_path}")
                        try:
                            os.remove(file_path)
                            removed_count += 1
                        except Exception as e:
                            logger.error(f"Error removing orphaned media {file_path}: {e}")
                        continue
                
                # Check for orphaned NFO files
                if file_lower.endswith('.nfo'):
                    base_name = os.path.splitext(file)[0]
                    if base_name not in video_files_in_dest:
                        logger.info(f"Removing orphaned NFO: {file_path}")
                        try:
                            os.remove(file_path)
                            removed_count += 1
                        except Exception as e:
                            logger.error(f"Error removing orphaned NFO {file_path}: {e}")

            # Cleanup empty directories
            if not os.listdir(root) and root != dest_root:
                try:
                    os.rmdir(root)
                    logger.info(f"Removed empty directory: {root}")
                except Exception:
                    pass

        # 3. Cleanup orphaned entries in .failed list
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

    return removed_count

def scan_mixed_folder_batches(path: str, skip_files: set[str]):
    """Recursively scans for video files and groups them by folder, filtering out skipped ones and respecting .ignore files."""
    video_extensions = ('.mkv', '.mp4', '.avi', '.mov', '.m4v', '.m2ts')
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
        
        # Check if this is a BD folder (contains BDMV)
        if 'BDMV' in dirs:
            # Find the largest .m2ts file in the BDMV/STREAM directory
            stream_dir = os.path.join(root, 'BDMV', 'STREAM')
            if os.path.exists(stream_dir):
                largest_file = None
                max_size = -1
                for f in os.listdir(stream_dir):
                    if f.lower().endswith('.m2ts'):
                        f_path = os.path.join(stream_dir, f)
                        f_size = os.path.getsize(f_path)
                        if f_size > max_size:
                            max_size = f_size
                            largest_file = f_path
                
                if largest_file:
                    full_path = os.path.abspath(largest_file)
                    if full_path not in skip_files:
                        # For BD folders, we use the folder name for identification
                        # but we yield the largest m2ts file as the file to process
                        batch.append(full_path)
            
            # Don't recurse into BDMV or other subdirs of a BD folder
            dirs[:] = []
        else:
            for file in files:
                if file.lower().endswith(video_extensions):
                    full_path = os.path.abspath(os.path.join(root, file))
                    if full_path not in skip_files:
                        batch.append(full_path)
        
        if batch:
            yield root, batch
