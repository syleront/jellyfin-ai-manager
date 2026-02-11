#!/usr/bin/env python3
"""
Test script for external audio and subtitle detection functionality.
Creates a mock directory structure to verify the external media linking works correctly.
"""

import os
import sys
import tempfile
import shutil

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.utils.fs_utils import find_external_audio_and_subtitles, create_relative_symlink, link_external_media


def create_test_structure():
    """Create a test directory structure similar to the example in requirements."""
    test_dir = tempfile.mkdtemp(prefix="jellyfin_test_")
    print(f"Creating test structure in: {test_dir}")
    
    # Create main series folder
    series_dir = os.path.join(test_dir, "[ANK-Raws] Haibane Renmei")
    os.makedirs(series_dir)
    
    # Create Russian Sound folder
    audio_dir = os.path.join(series_dir, "Russian Sound [Reanimedia]")
    os.makedirs(audio_dir)
    
    # Create Russian Subtitles folder
    subs_base_dir = os.path.join(series_dir, "Russian Subtitles [Reanimedia]")
    subs_dir = os.path.join(subs_base_dir, "Inscriptions [ass]")
    os.makedirs(subs_dir)
    
    # Create video files
    video_files = []
    for i in range(1, 4):
        video_name = f"[ANK-Raws] Haibane Renmei - {i:02d} (BDrip 1920x1080 x264 FLAC Hi10P).mkv"
        video_path = os.path.join(series_dir, video_name)
        
        # Create empty video file
        with open(video_path, 'w') as f:
            f.write(f"Mock video file {i}")
        video_files.append(video_path)
        
        # Create corresponding audio file
        audio_name = f"[ANK-Raws] Haibane Renmei - {i:02d} (BDrip 1920x1080 x264 FLAC Hi10P).Reanimedia.mka"
        audio_path = os.path.join(audio_dir, audio_name)
        with open(audio_path, 'w') as f:
            f.write(f"Mock audio file {i}")
        
        # Create corresponding subtitle file
        sub_name = f"[ANK-Raws] Haibane Renmei - {i:02d} (BDrip 1920x1080 x264 FLAC Hi10P).Reanimedia_inscriptions.ass"
        sub_path = os.path.join(subs_dir, sub_name)
        with open(sub_path, 'w') as f:
            f.write(f"Mock subtitle file {i}")
    
    return test_dir, series_dir, video_files


def test_external_media_detection():
    """Test the external media detection functionality."""
    print("\n=== Testing External Media Detection ===\n")
    
    test_dir, series_dir, video_files = create_test_structure()
    
    try:
        for video_file in video_files:
            print(f"\nTesting video: {os.path.basename(video_file)}")
            
            # Find external media
            external_files = find_external_audio_and_subtitles(video_file)
            
            print(f"  Found {len(external_files['audio'])} audio file(s)")
            for audio_src, audio_name in external_files['audio']:
                print(f"    - {audio_name}")
            
            print(f"  Found {len(external_files['subtitles'])} subtitle file(s)")
            for sub_src, sub_name in external_files['subtitles']:
                print(f"    - {sub_name}")
            
            # Test symlink creation with renaming (mimicking actual processor behavior)
            dest_dir = os.path.join(test_dir, "dest")
            os.makedirs(dest_dir, exist_ok=True)
            
            print("\n  Creating symlinks with renamed files (as processor does)...")
            
            # Simulate the renamed video file in dest (e.g., "Haibane Renmei - S1E01.mkv")
            # Extract episode number from filename like "[ANK-Raws] Haibane Renmei - 01 (BDrip...)mkv"
            basename = os.path.basename(video_file)
            # Find the number pattern (e.g., "01" or "02")
            import re
            match = re.search(r' - (\d+) ', basename)
            episode_num = match.group(1) if match else "01"
            
            renamed_video = os.path.join(dest_dir, f"Haibane Renmei - S1E{episode_num}.mkv")
            shutil.copy2(video_file, renamed_video)
            
            # Use link_external_media function (as processor does)
            linked = link_external_media(video_file, renamed_video, external_files)
            print(f"    Linked {linked} external media files")
        
        print("\n=== Destination Directory Structure ===\n")
        dest_dir = os.path.join(test_dir, "dest")
        for item in sorted(os.listdir(dest_dir)):
            print(f"  {item}")
        
        print("\n✓ Test completed successfully!")
        
    finally:
        # Cleanup
        print(f"\nCleaning up test directory: {test_dir}")
        shutil.rmtree(test_dir)


if __name__ == "__main__":
    test_external_media_detection()
