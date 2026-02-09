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
