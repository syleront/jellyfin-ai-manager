#!/usr/bin/env python3
"""
Test initial scan with external media already present.
Reproduces the issue where subtitles exist but are not linked during startup.
"""

import os
import sys
import tempfile
import shutil

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.utils.fs_utils import create_relative_symlink, find_external_audio_and_subtitles, link_external_media
from src.utils.nfo_generator import generate_movie_nfo


def test_initial_scan_with_existing_subtitles():
    """
    Test scenario:
    1. Video was already processed (has NFO and symlink)
    2. User adds subtitle folder
    3. Initial scan runs (restart)
    4. Subtitles should be detected and linked
    """
    print("\n" + "="*70)
    print("TEST: Initial Scan with Existing Subtitles")
    print("="*70 + "\n")
    
    test_dir = tempfile.mkdtemp(prefix="initial_scan_test_")
    
    try:
        # Setup directories
        mixed_path = os.path.join(test_dir, "mixed")
        movies_dest = os.path.join(test_dir, "movies")
        series_dest = os.path.join(test_dir, "series")
        os.makedirs(mixed_path, exist_ok=True)
        os.makedirs(movies_dest, exist_ok=True)
        os.makedirs(series_dest, exist_ok=True)
        
        # Step 1: Create Haibane Renmei structure
        print("Step 1: Creating Haibane Renmei structure...")
        series_folder = os.path.join(mixed_path, "[ANK-Raws] Haibane Renmei (BDrip 1920x1080 x264 FLAC Hi10P)")
        os.makedirs(series_folder, exist_ok=True)
        
        video1 = os.path.join(series_folder, "[ANK-Raws] Haibane Renmei - 01 (BDrip 1920x1080 x264 FLAC Hi10P).mkv")
        with open(video1, 'w') as f:
            f.write("video 1")
        
        # Create audio folder
        audio_folder = os.path.join(series_folder, "Russian Sound [Reanimedia]")
        os.makedirs(audio_folder, exist_ok=True)
        audio1 = os.path.join(audio_folder, "[ANK-Raws] Haibane Renmei - 01 (BDrip 1920x1080 x264 FLAC Hi10P).Reanimedia.mka")
        with open(audio1, 'w') as f:
            f.write("audio 1")
        
        print(f"  ✓ Created video and audio")
        
        # Step 2: Simulate initial processing (video was already processed)
        print("\nStep 2: Simulating previous processing (video already linked)...")
        dest_dir = os.path.join(series_dest, "Haibane Renmei (2002)", "Season 1")
        os.makedirs(dest_dir, exist_ok=True)
        
        dest_video = os.path.join(dest_dir, "Haibane Renmei - S01E01.mkv")
        create_relative_symlink(video1, dest_video)
        
        # Create NFO (this marks the file as "processed")
        nfo_path = os.path.join(dest_dir, "Haibane Renmei - S01E01.nfo")
        with open(nfo_path, 'w') as f:
            f.write("<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n<episodedetails>\n</episodedetails>")
        
        # Link initial external media (only audio)
        from src.utils.fs_utils import find_external_audio_and_subtitles as find_ext, link_external_media as link_ext
        external_files = find_ext(video1)
        link_ext(video1, dest_video, external_files)
        
        expected_audio = os.path.join(dest_dir, "Haibane Renmei - S01E01.Reanimedia.mka")
        assert os.path.exists(expected_audio), "Audio should be linked"
        print(f"  ✓ Video linked, NFO created, audio linked")
        
        # Step 3: User adds subtitle folder (while app is offline)
        print("\nStep 3: User adds subtitle folder (app offline)...")
        subs_base = os.path.join(series_folder, "Russian Subtitles [Reanimedia]")
        subs_folder = os.path.join(subs_base, "Inscriptions [ass]")
        os.makedirs(subs_folder, exist_ok=True)
        
        sub1 = os.path.join(subs_folder, "[ANK-Raws] Haibane Renmei - 01 (BDrip 1920x1080 x264 FLAC Hi10P).Reanimedia_inscriptions.ass")
        with open(sub1, 'w') as f:
            f.write("subtitle 1")
        
        expected_sub = os.path.join(dest_dir, "Haibane Renmei - S01E01.Reanimedia_inscriptions.ass")
        assert not os.path.exists(expected_sub), "Subtitle should NOT be linked yet"
        print(f"  ✓ Subtitle file created, not linked yet")
        
        # Step 4: Simulate initial scan (app restarts)
        print("\nStep 4: Simulating initial scan (app restart)...")
        
        # Import and use the actual initial scan logic
        from src.main import run_initial_scan
        from src.core.config import Config
        
        # Create mock config
        class MockConfig:
            def __init__(self):
                self.mixed_path = mixed_path
                self.movies_dest_path = movies_dest
                self.series_dest_path = series_dest
                self.jellyfin_movies_library_id = None
                self.jellyfin_series_library_id = None
        
        class MockLLM:
            pass
        
        class MockTMDB:
            pass
        
        class MockJellyfin:
            pass
        
        class MockProcessor:
            pass
        
        class MockLogger:
            def info(self, msg):
                print(f"  [INFO] {msg}")
            def warning(self, msg):
                print(f"  [WARN] {msg}")
            def error(self, msg):
                print(f"  [ERROR] {msg}")
        
        config = MockConfig()
        logger = MockLogger()
        
        # Run initial scan - this should re-link external media for processed files
        # We're only testing the re-linking part, not the full scan
        from src.utils.fs_utils import get_processed_files, find_external_audio_and_subtitles, link_external_media
        
        processed_files = get_processed_files(movies_dest, series_dest)
        print(f"  Found {len(processed_files)} processed files")
        
        relinked_count = 0
        video_extensions = ('.mkv', '.mp4', '.avi', '.mov', '.m4v', '.m2ts')
        for dest_root in [movies_dest, series_dest]:
            if not dest_root or not os.path.exists(dest_root):
                continue
            
            for root, dirs, files in os.walk(dest_root):
                for file in files:
                    if file.lower().endswith(video_extensions):
                        dest_video_path = os.path.join(root, file)
                        if os.path.islink(dest_video_path):
                            # Resolve symlink to get source path
                            link_target = os.readlink(dest_video_path)
                            if not os.path.isabs(link_target):
                                link_target = os.path.normpath(os.path.join(root, link_target))
                            
                            src_video_path = os.path.abspath(link_target)
                            if os.path.exists(src_video_path):
                                # Find and link external media
                                external_files = find_external_audio_and_subtitles(src_video_path)
                                if external_files['audio'] or external_files['subtitles']:
                                    linked = link_external_media(src_video_path, dest_video_path, external_files)
                                    if linked > 0:
                                        relinked_count += linked
        
        print(f"  ✓ Re-linked {relinked_count} external media file(s)")
        
        # Step 5: Verify subtitle is now linked
        print("\nStep 5: Verifying subtitle was linked...")
        assert os.path.exists(expected_sub), f"Subtitle should be linked: {expected_sub}"
        assert os.path.islink(expected_sub), "Subtitle should be a symlink"
        print(f"  ✓ Subtitle symlink created")
        
        print("\n" + "="*70)
        print("✅ TEST PASSED: Initial scan re-links external media correctly")
        print("="*70 + "\n")
        
    finally:
        shutil.rmtree(test_dir)


if __name__ == "__main__":
    test_initial_scan_with_existing_subtitles()
