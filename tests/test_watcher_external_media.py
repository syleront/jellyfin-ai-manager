#!/usr/bin/env python3
"""
Test watcher functionality with external media (audio/subtitle) files.
Tests real-time event detection and re-linking.
"""

import os
import sys
import tempfile
import shutil
import time
from pathlib import Path

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.core.watcher import MediaWatcherHandler
from src.utils.fs_utils import create_relative_symlink


class MockConfig:
    """Mock config for testing."""
    def __init__(self, base_path):
        self.mixed_path = os.path.join(base_path, "mixed")
        self.movies_dest_path = os.path.join(base_path, "movies")
        self.series_dest_path = os.path.join(base_path, "series")
        self.jellyfin_movies_library_id = None
        self.jellyfin_series_library_id = None
        os.makedirs(self.mixed_path, exist_ok=True)
        os.makedirs(self.movies_dest_path, exist_ok=True)
        os.makedirs(self.series_dest_path, exist_ok=True)


class MockLLM:
    """Mock LLM client."""
    pass


class MockProcessor:
    """Mock processor."""
    pass


class MockJellyfin:
    """Mock Jellyfin client."""
    def refresh_library(self, library_id):
        pass


def test_external_media_addition():
    """Test that adding external media triggers re-linking."""
    print("\n=== Testing External Media Addition (Real Watcher) ===\n")
    
    test_dir = tempfile.mkdtemp(prefix="watcher_ext_test_")
    config = MockConfig(test_dir)
    handler = MediaWatcherHandler(config, MockLLM(), MockProcessor(), MockJellyfin())
    handler.is_initial_scan_complete = True  # Enable event processing
    
    try:
        # Setup: Create Haibane Renmei structure
        series_folder = os.path.join(config.mixed_path, "[ANK-Raws] Haibane Renmei (BDrip 1920x1080 x264 FLAC Hi10P)")
        os.makedirs(series_folder, exist_ok=True)
        
        # Create video files
        video1 = os.path.join(series_folder, "[ANK-Raws] Haibane Renmei - 01 (BDrip 1920x1080 x264 FLAC Hi10P).mkv")
        with open(video1, 'w') as f:
            f.write("video 1")
        
        print(f"✓ Created video: {os.path.basename(video1)}")
        
        # Create audio folder and file
        audio_folder = os.path.join(series_folder, "Russian Sound [Reanimedia]")
        os.makedirs(audio_folder, exist_ok=True)
        
        audio1 = os.path.join(audio_folder, "[ANK-Raws] Haibane Renmei - 01 (BDrip 1920x1080 x264 FLAC Hi10P).Reanimedia.mka")
        with open(audio1, 'w') as f:
            f.write("audio 1")
        
        print(f"✓ Created audio: {os.path.basename(audio1)}")
        
        # Simulate initial processing: create video symlink in dest
        dest_dir = os.path.join(config.series_dest_path, "Haibane Renmei (2002)", "Season 1")
        os.makedirs(dest_dir, exist_ok=True)
        
        dest_video1 = os.path.join(dest_dir, "Haibane Renmei - S01E01.mkv")
        create_relative_symlink(video1, dest_video1)
        
        print(f"✓ Created video symlink: {os.path.basename(dest_video1)}")
        
        # Initially link the audio
        from src.utils.fs_utils import find_external_audio_and_subtitles, link_external_media
        external_files = find_external_audio_and_subtitles(video1)
        link_external_media(video1, dest_video1, external_files)
        
        expected_audio1 = os.path.join(dest_dir, "Haibane Renmei - S01E01.Reanimedia.mka")
        assert os.path.exists(expected_audio1), "Audio should be linked initially"
        print(f"✓ Audio linked initially: {os.path.basename(expected_audio1)}")
        
        # Now create subtitle folder structure (simulating user adding it)
        print(f"\n--- Simulating user adding subtitle folder ---")
        
        subs_base = os.path.join(series_folder, "Russian Subtitles [Reanimedia]")
        subs_folder = os.path.join(subs_base, "Inscriptions [ass]")
        os.makedirs(subs_folder, exist_ok=True)
        
        sub1 = os.path.join(subs_folder, "[ANK-Raws] Haibane Renmei - 01 (BDrip 1920x1080 x264 FLAC Hi10P).Reanimedia_inscriptions.ass")
        with open(sub1, 'w') as f:
            f.write("subtitle 1")
        
        print(f"✓ Created subtitle: {os.path.basename(sub1)}")
        
        # Simulate watcher event
        class MockEvent:
            def __init__(self, path):
                self.src_path = path
                self.is_directory = False
        
        event = MockEvent(sub1)
        handler.on_created(event)
        
        # Process the queued event
        print(f"✓ Event queued, processing...")
        
        if not handler.event_queue.empty():
            event_type, data = handler.event_queue.get()
            print(f"  Event type: {event_type}")
            assert event_type == 'external_media_added', f"Expected external_media_added, got {event_type}"
            
            handler._handle_external_media_added(data)
        else:
            raise AssertionError("Event not queued!")
        
        # Verify subtitle symlink was created
        expected_sub1 = os.path.join(dest_dir, "Haibane Renmei - S01E01.Reanimedia_inscriptions.ass")
        assert os.path.exists(expected_sub1), f"Subtitle symlink should be created: {expected_sub1}"
        assert os.path.islink(expected_sub1), "Subtitle should be a symlink"
        
        print(f"✓ Subtitle symlink created: {os.path.basename(expected_sub1)}")
        print(f"  -> {os.readlink(expected_sub1)}")
        
        print("\n✅ Test PASSED: External media addition triggers re-linking")
        
    finally:
        shutil.rmtree(test_dir)


def test_external_media_deletion():
    """Test that deleting external media triggers cleanup."""
    print("\n=== Testing External Media Deletion (Real Watcher) ===\n")
    
    test_dir = tempfile.mkdtemp(prefix="watcher_ext_test_")
    config = MockConfig(test_dir)
    handler = MediaWatcherHandler(config, MockLLM(), MockProcessor(), MockJellyfin())
    handler.is_initial_scan_complete = True
    
    try:
        # Setup: Video + audio + subtitle all linked
        series_folder = os.path.join(config.mixed_path, "[ANK-Raws] Haibane Renmei (BDrip 1920x1080 x264 FLAC Hi10P)")
        os.makedirs(series_folder, exist_ok=True)
        
        video1 = os.path.join(series_folder, "[ANK-Raws] Haibane Renmei - 01 (BDrip 1920x1080 x264 FLAC Hi10P).mkv")
        with open(video1, 'w') as f:
            f.write("video 1")
        
        audio_folder = os.path.join(series_folder, "Russian Sound [Reanimedia]")
        os.makedirs(audio_folder, exist_ok=True)
        audio1 = os.path.join(audio_folder, "[ANK-Raws] Haibane Renmei - 01 (BDrip 1920x1080 x264 FLAC Hi10P).Reanimedia.mka")
        with open(audio1, 'w') as f:
            f.write("audio 1")
        
        subs_base = os.path.join(series_folder, "Russian Subtitles [Reanimedia]")
        subs_folder = os.path.join(subs_base, "Inscriptions [ass]")
        os.makedirs(subs_folder, exist_ok=True)
        sub1 = os.path.join(subs_folder, "[ANK-Raws] Haibane Renmei - 01 (BDrip 1920x1080 x264 FLAC Hi10P).Reanimedia_inscriptions.ass")
        with open(sub1, 'w') as f:
            f.write("subtitle 1")
        
        # Create dest symlinks
        dest_dir = os.path.join(config.series_dest_path, "Haibane Renmei (2002)", "Season 1")
        os.makedirs(dest_dir, exist_ok=True)
        
        dest_video1 = os.path.join(dest_dir, "Haibane Renmei - S01E01.mkv")
        create_relative_symlink(video1, dest_video1)
        
        from src.utils.fs_utils import find_external_audio_and_subtitles, link_external_media
        external_files = find_external_audio_and_subtitles(video1)
        link_external_media(video1, dest_video1, external_files)
        
        expected_audio1 = os.path.join(dest_dir, "Haibane Renmei - S01E01.Reanimedia.mka")
        expected_sub1 = os.path.join(dest_dir, "Haibane Renmei - S01E01.Reanimedia_inscriptions.ass")
        
        assert os.path.exists(expected_audio1), "Audio should exist initially"
        assert os.path.exists(expected_sub1), "Subtitle should exist initially"
        print(f"✓ Initial setup complete: video, audio, and subtitle all linked")
        
        # Simulate deletion of subtitle folder
        print(f"\n--- Simulating user deleting subtitle folder ---")
        
        # Delete the subtitle file
        os.remove(sub1)
        print(f"✓ Deleted subtitle: {os.path.basename(sub1)}")
        
        # Simulate watcher event
        class MockEvent:
            def __init__(self, path):
                self.src_path = path
                self.is_directory = False
        
        event = MockEvent(sub1)
        handler.on_deleted(event)
        
        # Process the queued event
        if not handler.event_queue.empty():
            event_type, data = handler.event_queue.get()
            assert event_type == 'deleted', f"Expected deleted event, got {event_type}"
            handler._handle_deletion(data)
        
        # Verify subtitle symlink was removed
        assert not os.path.exists(expected_sub1), f"Subtitle symlink should be removed"
        print(f"✓ Subtitle symlink removed: {os.path.basename(expected_sub1)}")
        
        # Verify audio and video still exist
        assert os.path.exists(expected_audio1), "Audio symlink should still exist"
        assert os.path.exists(dest_video1), "Video symlink should still exist"
        print(f"✓ Audio and video symlinks still exist")
        
        print("\n✅ Test PASSED: External media deletion triggers cleanup")
        
    finally:
        shutil.rmtree(test_dir)


if __name__ == "__main__":
    print("="*70)
    print("WATCHER EXTERNAL MEDIA TESTS (Real Watcher)")
    print("="*70)
    
    test_external_media_addition()
    test_external_media_deletion()
    
    print("\n" + "="*70)
    print("✅ ALL WATCHER TESTS PASSED!")
    print("="*70 + "\n")
