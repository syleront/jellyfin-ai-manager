#!/usr/bin/env python3
"""
Real-world test: Haibane Renmei structure with folder addition/deletion.
Simulates the exact scenario described by the user.
"""

import os
import sys
import tempfile
import shutil

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.core.watcher import MediaWatcherHandler
from src.utils.fs_utils import create_relative_symlink, find_external_audio_and_subtitles, link_external_media


class MockConfig:
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
    pass


class MockProcessor:
    pass


class MockJellyfin:
    def refresh_library(self, library_id):
        pass


def create_haibane_structure(base_path):
    """Create the exact Haibane Renmei structure from user's example."""
    series_folder = os.path.join(base_path, "[ANK-Raws] Haibane Renmei (BDrip 1920x1080 x264 FLAC Hi10P)")
    os.makedirs(series_folder, exist_ok=True)
    
    # Create video files (episodes 1-3)
    videos = []
    for i in range(1, 4):
        video = os.path.join(series_folder, f"[ANK-Raws] Haibane Renmei - {i:02d} (BDrip 1920x1080 x264 FLAC Hi10P).mkv")
        with open(video, 'w') as f:
            f.write(f"video {i}")
        videos.append(video)
    
    # Create Russian Sound folder with audio files
    audio_folder = os.path.join(series_folder, "Russian Sound [Reanimedia]")
    os.makedirs(audio_folder, exist_ok=True)
    
    audios = []
    for i in range(1, 4):
        audio = os.path.join(audio_folder, f"[ANK-Raws] Haibane Renmei - {i:02d} (BDrip 1920x1080 x264 FLAC Hi10P).Reanimedia.mka")
        with open(audio, 'w') as f:
            f.write(f"audio {i}")
        audios.append(audio)
    
    # DO NOT create subtitle folder yet - we'll add it later to simulate user action
    
    return {
        'series_folder': series_folder,
        'videos': videos,
        'audios': audios
    }


def add_subtitle_folder(series_folder):
    """Add the Russian Subtitles folder (simulating user adding it)."""
    subs_base = os.path.join(series_folder, "Russian Subtitles [Reanimedia]")
    
    # Create Fonts folder (empty)
    fonts_folder = os.path.join(subs_base, "Fonts")
    os.makedirs(fonts_folder, exist_ok=True)
    
    # Create Full [ass] folder (empty)
    full_folder = os.path.join(subs_base, "Full [ass]")
    os.makedirs(full_folder, exist_ok=True)
    
    # Create Inscriptions [ass] folder with subtitle files
    inscriptions_folder = os.path.join(subs_base, "Inscriptions [ass]")
    os.makedirs(inscriptions_folder, exist_ok=True)
    
    subs = []
    for i in range(1, 4):
        sub = os.path.join(inscriptions_folder, f"[ANK-Raws] Haibane Renmei - {i:02d} (BDrip 1920x1080 x264 FLAC Hi10P).Reanimedia_inscriptions.ass")
        with open(sub, 'w') as f:
            f.write(f"subtitle {i}")
        subs.append(sub)
    
    return subs


def test_real_world_scenario():
    """Test the exact real-world scenario: add/remove subtitle folder."""
    print("\n" + "="*70)
    print("REAL-WORLD TEST: Haibane Renmei Subtitle Folder Add/Remove")
    print("="*70 + "\n")
    
    test_dir = tempfile.mkdtemp(prefix="haibane_test_")
    config = MockConfig(test_dir)
    
    try:
        # Step 1: Create initial structure (without subtitles)
        print("Step 1: Creating initial Haibane Renmei structure...")
        structure = create_haibane_structure(config.mixed_path)
        print(f"  ✓ Created {len(structure['videos'])} videos")
        print(f"  ✓ Created {len(structure['audios'])} audio files")
        print(f"  ✗ No subtitles yet (will add later)")
        
        # Step 2: Simulate initial processing (what the processor would do)
        print("\nStep 2: Initial processing (creating symlinks)...")
        dest_dir = os.path.join(config.series_dest_path, "Haibane Renmei (2002)", "Season 1")
        os.makedirs(dest_dir, exist_ok=True)
        
        dest_videos = []
        for i, video_src in enumerate(structure['videos'], 1):
            dest_video = os.path.join(dest_dir, f"Haibane Renmei - S01E{i:02d}.mkv")
            create_relative_symlink(video_src, dest_video)
            
            # Link external media (only audio at this point)
            external = find_external_audio_and_subtitles(video_src)
            link_external_media(video_src, dest_video, external)
            
            dest_videos.append(dest_video)
            print(f"  ✓ Episode {i}: video + {len(external['audio'])} audio, {len(external['subtitles'])} subtitles")
        
        # Verify only audio symlinks exist, no subtitles
        for i in range(1, 4):
            expected_audio = os.path.join(dest_dir, f"Haibane Renmei - S01E{i:02d}.Reanimedia.mka")
            expected_sub = os.path.join(dest_dir, f"Haibane Renmei - S01E{i:02d}.Reanimedia_inscriptions.ass")
            
            assert os.path.exists(expected_audio), f"Episode {i} audio should exist"
            assert not os.path.exists(expected_sub), f"Episode {i} subtitle should NOT exist yet"
        
        print(f"\n  ✓ Verified: All audio symlinks created, no subtitle symlinks")
        
        # Step 3: Simulate watcher
        print("\nStep 3: Starting watcher...")
        handler = MediaWatcherHandler(config, MockLLM(), MockProcessor(), MockJellyfin())
        handler.is_initial_scan_complete = True
        print(f"  ✓ Watcher ready")
        
        # Step 4: User adds subtitle folder
        print("\nStep 4: User adds 'Russian Subtitles [Reanimedia]' folder...")
        subs = add_subtitle_folder(structure['series_folder'])
        print(f"  ✓ Created {len(subs)} subtitle files")
        
        # Step 5: Simulate watcher events for each subtitle file
        print("\nStep 5: Processing watcher events for new subtitles...")
        
        class MockEvent:
            def __init__(self, path):
                self.src_path = path
                self.is_directory = False
        
        for sub in subs:
            event = MockEvent(sub)
            handler.on_created(event)
        
        # Process all queued events
        events_processed = 0
        while not handler.event_queue.empty():
            event_type, data = handler.event_queue.get()
            if event_type == 'external_media_added':
                handler._handle_external_media_added(data)
                events_processed += 1
        
        print(f"  ✓ Processed {events_processed} external media addition events")
        
        # Step 6: Verify subtitle symlinks were created
        print("\nStep 6: Verifying subtitle symlinks were created...")
        for i in range(1, 4):
            expected_sub = os.path.join(dest_dir, f"Haibane Renmei - S01E{i:02d}.Reanimedia_inscriptions.ass")
            assert os.path.exists(expected_sub), f"Episode {i} subtitle symlink should exist"
            assert os.path.islink(expected_sub), f"Episode {i} subtitle should be a symlink"
            print(f"  ✓ Episode {i}: subtitle symlink created")
        
        print("\n" + "="*70)
        print("✅ TEST PASSED: Subtitle folder addition works correctly!")
        print("="*70)
        
        # Step 7: Now test deletion
        print("\nStep 7: User deletes 'Russian Subtitles [Reanimedia]' folder...")
        
        # Delete subtitle files and trigger events
        for sub in subs:
            os.remove(sub)
            event = MockEvent(sub)
            handler.on_deleted(event)
        
        # Process deletion events
        events_processed = 0
        while not handler.event_queue.empty():
            event_type, data = handler.event_queue.get()
            if event_type == 'deleted':
                handler._handle_deletion(data)
                events_processed += 1
        
        print(f"  ✓ Processed {events_processed} deletion events")
        
        # Step 8: Verify subtitle symlinks were removed
        print("\nStep 8: Verifying subtitle symlinks were removed...")
        for i in range(1, 4):
            expected_sub = os.path.join(dest_dir, f"Haibane Renmei - S01E{i:02d}.Reanimedia_inscriptions.ass")
            expected_audio = os.path.join(dest_dir, f"Haibane Renmei - S01E{i:02d}.Reanimedia.mka")
            expected_video = os.path.join(dest_dir, f"Haibane Renmei - S01E{i:02d}.mkv")
            
            assert not os.path.exists(expected_sub), f"Episode {i} subtitle symlink should be removed"
            assert os.path.exists(expected_audio), f"Episode {i} audio should still exist"
            assert os.path.exists(expected_video), f"Episode {i} video should still exist"
            print(f"  ✓ Episode {i}: subtitle removed, audio and video intact")
        
        print("\n" + "="*70)
        print("✅ TEST PASSED: Subtitle folder deletion works correctly!")
        print("="*70 + "\n")
        
    finally:
        shutil.rmtree(test_dir)


if __name__ == "__main__":
    test_real_world_scenario()
