import os
import re
import logging

logger = logging.getLogger(__name__)

def escape_filename(filename: str) -> str:
    """
    Escapes characters that are invalid in filenames across Windows, Linux, and macOS.
    Windows invalid: < > : " / \ | ? *
    Linux/macOS invalid: / (and null byte)
    Also removes trailing dots and spaces which are problematic on Windows.
    """
    if not filename:
        return ""
    # Replace invalid characters with an underscore
    escaped = re.sub(r'[<>:"/\\|?*]', '_', filename)
    # Remove trailing dots and spaces
    escaped = escaped.rstrip('. ')
    return escaped

def create_relative_symlink(src: str, dst: str) -> bool:
    """Creates a relative symlink."""
    try:
        if os.path.exists(dst):
            return True
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        
        # Calculate relative path from dst to src
        rel_src = os.path.relpath(src, os.path.dirname(dst))
        
        os.symlink(rel_src, dst)
        return True
    except Exception as e:
        logger.error(f"Failed to create relative symlink from {src} to {dst}: {e}")
        return False

def mark_as_failed(file_path: str, base_dest_path: str, mixed_path: str):
    """Adds the relative path of the failed file to a .failed list in the target folder."""
    try:
        rel_path = os.path.relpath(file_path, mixed_path)
        failed_list_path = os.path.join(base_dest_path, ".failed")
        
        # Read existing to avoid duplicates
        existing = set()
        if os.path.exists(failed_list_path):
            with open(failed_list_path, 'r', encoding='utf-8') as f:
                existing = {line.strip() for line in f if line.strip()}
        
        if rel_path not in existing:
            with open(failed_list_path, 'a', encoding='utf-8') as f:
                f.write(rel_path + "\n")
            logger.info(f"Added to failed list in {os.path.basename(base_dest_path)}: {rel_path}")
    except Exception as e:
        logger.error(f"Failed to update .failed list for {file_path}: {e}")

def get_failed_files(movies_path: str, series_path: str, mixed_path: str) -> set[str]:
    """Reads .failed lists from target folders and returns a set of absolute source paths."""
    failed_sources = set()
    for dest_root in [movies_path, series_path]:
        failed_list_path = os.path.join(dest_root, ".failed")
        if os.path.exists(failed_list_path):
            try:
                with open(failed_list_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        rel_path = line.strip()
                        if rel_path:
                            abs_path = os.path.abspath(os.path.join(mixed_path, rel_path))
                            failed_sources.add(abs_path)
            except Exception as e:
                logger.error(f"Error reading failed list {failed_list_path}: {e}")
    return failed_sources

def get_processed_files(movies_path: str, series_path: str) -> set[str]:
    """
    Scans destination folders for .nfo files and resolves their corresponding source files.
    Returns a set of absolute paths to source files that are already processed.
    """
    processed_sources = set()
    video_extensions = ('.mkv', '.mp4', '.avi', '.mov', '.m4v', '.m2ts')
    
    for dest_root in [movies_path, series_path]:
        if not dest_root or not os.path.exists(dest_root):
            continue
            
        for root, _, files in os.walk(dest_root):
            for file in files:
                if file.lower().endswith(video_extensions):
                    video_path = os.path.join(root, file)
                    nfo_path = os.path.splitext(video_path)[0] + ".nfo"
                    
                    if os.path.exists(nfo_path):
                        # Resolve symlink to get the original source file path
                        if os.path.islink(video_path):
                            try:
                                # os.readlink might return a relative path
                                link_target = os.readlink(video_path)
                                if not os.path.isabs(link_target):
                                    link_target = os.path.normpath(os.path.join(root, link_target))
                                
                                target_abs = os.path.abspath(link_target)
                                if os.path.exists(target_abs):
                                    processed_sources.add(target_abs)
                            except Exception:
                                pass
    return processed_sources

def find_external_audio_and_subtitles(video_file_path: str) -> dict:
    """
    Find external audio and subtitle files for a given video file.
    Searches in sibling directories for files matching the video filename.
    
    Returns a dict with:
    {
        'audio': [(src_path, suggested_dest_name), ...],
        'subtitles': [(src_path, suggested_dest_name), ...]
    }
    """
    audio_extensions = ('.mka', '.mp3', '.aac', '.ac3', '.dts', '.flac')
    subtitle_extensions = ('.ass', '.srt', '.ssa', '.sub', '.vtt')
    
    result = {
        'audio': [],
        'subtitles': []
    }
    
    video_dir = os.path.dirname(video_file_path)
    video_basename = os.path.basename(video_file_path)
    video_name_no_ext = os.path.splitext(video_basename)[0]
    
    logger.debug(f"Searching for external media for: {video_basename}")
    
    # Search parent directory and its subdirectories
    parent_dir = os.path.dirname(video_dir)
    if not os.path.exists(parent_dir):
        parent_dir = video_dir
    
    # Search all directories at the same level as the video file or in subdirectories
    search_dirs = []
    
    # 1. Search in the same directory as the video file
    search_dirs.append(video_dir)
    
    # 2. If video is in a subdirectory, search parent's children (sibling directories)
    if parent_dir != video_dir:
        try:
            for item in os.listdir(parent_dir):
                item_path = os.path.join(parent_dir, item)
                if os.path.isdir(item_path) and item_path != video_dir:
                    search_dirs.append(item_path)
        except Exception as e:
            logger.error(f"Error listing parent directory {parent_dir}: {e}")
    
    # 3. Also search subdirectories of the video directory
    try:
        for item in os.listdir(video_dir):
            item_path = os.path.join(video_dir, item)
            if os.path.isdir(item_path):
                search_dirs.append(item_path)
    except Exception as e:
        logger.error(f"Error listing video directory {video_dir}: {e}")
    
    if search_dirs:
        logger.debug(f"Searching {len(search_dirs)} directories for external media")
    
    # Search for matching files
    seen_files = set()  # Track files to avoid duplicates
    for search_dir in search_dirs:
        try:
            # Walk through subdirectories as well
            for root, _, files in os.walk(search_dir):
                for file in files:
                    file_lower = file.lower()
                    file_path = os.path.join(root, file)
                    
                    # Skip if already seen
                    if file_path in seen_files:
                        continue
                    
                    # Check if the file name starts with the video name
                    if file.startswith(video_name_no_ext):
                        if file_lower.endswith(audio_extensions):
                            # Use the original filename for the hardlink
                            result['audio'].append((file_path, file))
                            seen_files.add(file_path)
                            logger.info(f"Found external audio: {file_path}")
                        elif file_lower.endswith(subtitle_extensions):
                            result['subtitles'].append((file_path, file))
                            seen_files.add(file_path)
                            logger.info(f"Found external subtitle: {file_path}")
        except Exception as e:
            logger.error(f"Error searching directory {search_dir}: {e}")
    
    return result

def link_external_media(video_src_path: str, video_dest_path: str, external_files: dict) -> int:
    """
    Create relative symlinks for external audio and subtitle files next to the video file.
    Renames external media files to match the destination video filename while preserving suffixes.
    
    Example:
        Source video: "[ANK-Raws] Haibane Renmei - 01.mkv"
        Dest video: "Haibane Renmei - S1E1.mkv"
        Source audio: "[ANK-Raws] Haibane Renmei - 01.Reanimedia.mka"
        Dest audio: "Haibane Renmei - S1E1.Reanimedia.mka"
    
    Args:
        video_src_path: The original source path of the video file
        video_dest_path: The destination path of the video file (symlink)
        external_files: Dict returned by find_external_audio_and_subtitles()
    
    Returns:
        Number of successfully created symlinks
    """
    linked_count = 0
    dest_dir = os.path.dirname(video_dest_path)
    
    video_src_name_no_ext = os.path.splitext(os.path.basename(video_src_path))[0]
    video_dest_name_no_ext = os.path.splitext(os.path.basename(video_dest_path))[0]
    
    # Link audio files
    for src_path, suggested_name in external_files.get('audio', []):
        suggested_name_no_ext = os.path.splitext(suggested_name)[0]
        ext = os.path.splitext(suggested_name)[1]
        
        # Extract suffix (language tag, commentary, etc.)
        # E.g., "[Original] Movie - 01.Reanimedia" with original name "[Original] Movie - 01"
        # -> suffix is ".Reanimedia"
        if suggested_name_no_ext.startswith(video_src_name_no_ext):
            suffix = suggested_name_no_ext[len(video_src_name_no_ext):]
        else:
            suffix = ""
        
        # New name: video_dest_name + suffix + extension
        new_name = video_dest_name_no_ext + suffix + ext
        dest_path = os.path.join(dest_dir, new_name)
        
        if create_relative_symlink(src_path, dest_path):
            linked_count += 1
    
    # Link subtitle files
    for src_path, suggested_name in external_files.get('subtitles', []):
        suggested_name_no_ext = os.path.splitext(suggested_name)[0]
        ext = os.path.splitext(suggested_name)[1]
        
        # Extract suffix
        if suggested_name_no_ext.startswith(video_src_name_no_ext):
            suffix = suggested_name_no_ext[len(video_src_name_no_ext):]
        else:
            suffix = ""
        
        # New name
        new_name = video_dest_name_no_ext + suffix + ext
        dest_path = os.path.join(dest_dir, new_name)
        
        if create_relative_symlink(src_path, dest_path):
            linked_count += 1
    
    return linked_count
