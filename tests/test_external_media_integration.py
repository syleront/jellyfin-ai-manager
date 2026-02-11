#!/usr/bin/env python3
"""
Integration test for external media (audio/subtitle) handling.
Tests initial scan, watcher events, and cleanup scenarios.
"""

import os
import sys
import tempfile
import shutil
import time
from pathlib import Path

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.utils.fs_utils import find_external_audio_and_subtitles, link_external_media
from src.utils.scanner import cleanup_broken_links


def create_test_structure(base_dir):
    """Create a test directory structure with video and external media."""
    # Create mixed folder structure
    mixed = os.path.join(base_dir, "mixed")
    series_folder = os.path.join(mixed, "Test Series [2024]")
    os.makedirs(series_folder, exist_ok=True)
    
    # Create main video file
    video_file = os.path.join(series_folder, "[Group] Test Series - 01 [1080p].mkv")
    with open(video_file, 'w') as f:
        f.write("video content")
    
    # Create external media in subfolder
    # IMPORTANT: External media filenames must START with video filename (without extension)
    audio_folder = os.path.join(series_folder, "Audio")
    os.makedirs(audio_folder, exist_ok=True)
    
    # Audio file name starts with video name + suffix
    audio_file = os.path.join(audio_folder, "[Group] Test Series - 01 [1080p].Reanimedia.mka")
    with open(audio_file, 'w') as f:
        f.write("audio content")
    
    # Subtitle file name starts with video name + suffix
    sub_file = os.path.join(series_folder, "[Group] Test Series - 01 [1080p].rus.ass")
    with open(sub_file, 'w') as f:
        f.write("subtitle content")
    
    return {
        'mixed': mixed,
        'video': video_file,
        'audio': audio_file,
        'subtitle': sub_file,
        'series_folder': series_folder
    }


def test_initial_scan_external_media():
    """Test that external media is found and linked during initial scan."""
    print("\n=== Test 1: Initial Scan - External Media Detection ===\n")
    
    test_dir = tempfile.mkdtemp(prefix="ext_media_test_")
    
    try:
        # Setup
        structure = create_test_structure(test_dir)
        dest_dir = os.path.join(test_dir, "series", "Test Series (2024)", "Season 1")
        os.makedirs(dest_dir, exist_ok=True)
        
        # Create video symlink (simulating what processor does)
        dest_video = os.path.join(dest_dir, "Test Series - S01E01.mkv")
        os.symlink(
            os.path.relpath(structure['video'], dest_dir),
            dest_video
        )
        print(f"✓ Created video symlink: {os.path.basename(dest_video)}")
        
        # Find external media (simulating initial scan)
        external_files = find_external_audio_and_subtitles(structure['video'])
        print(f"\nFound external media: {external_files}")
        total_count = len(external_files.get('audio', [])) + len(external_files.get('subtitles', []))
        print(f"Total count: {total_count} (audio: {len(external_files.get('audio', []))}, subtitles: {len(external_files.get('subtitles', []))})")
        
        assert total_count == 2, f"Expected 2 external files, found {total_count}"
        
        # Link external media
        link_external_media(structure['video'], dest_video, external_files)
        print(f"\n✓ Linked external media")
        
        # Verify symlinks exist
        expected_audio = os.path.join(dest_dir, "Test Series - S01E01.Reanimedia.mka")
        expected_sub = os.path.join(dest_dir, "Test Series - S01E01.rus.ass")
        
        assert os.path.islink(expected_audio), f"Audio symlink not created: {expected_audio}"
        assert os.path.islink(expected_sub), f"Subtitle symlink not created: {expected_sub}"
        
        # Verify symlinks are valid (target exists)
        assert os.path.exists(expected_audio), f"Audio symlink is broken"
        assert os.path.exists(expected_sub), f"Subtitle symlink is broken"
        
        print(f"\n✓ Verified symlinks:")
        print(f"  - {os.path.basename(expected_audio)} -> {os.readlink(expected_audio)}")
        print(f"  - {os.path.basename(expected_sub)} -> {os.readlink(expected_sub)}")
        
        print("\n✅ Test 1 PASSED: External media linked correctly during initial scan")
        
    finally:
        shutil.rmtree(test_dir)


def test_watcher_add_external_media():
    """Test that adding external media file triggers symlink creation."""
    print("\n=== Test 2: Watcher - Add External Media ===\n")
    
    test_dir = tempfile.mkdtemp(prefix="ext_media_test_")
    
    try:
        # Setup: Video already processed
        structure = create_test_structure(test_dir)
        dest_dir = os.path.join(test_dir, "series", "Test Series (2024)", "Season 1")
        os.makedirs(dest_dir, exist_ok=True)
        
        dest_video = os.path.join(dest_dir, "Test Series - S01E01.mkv")
        os.symlink(
            os.path.relpath(structure['video'], dest_dir),
            dest_video
        )
        print(f"✓ Initial setup: video symlink exists")
        
        # Delete external media files (simulate they weren't there initially)
        os.remove(structure['audio'])
        os.remove(structure['subtitle'])
        print(f"✓ Removed external media files (simulating fresh state)")
        
        # Verify no external media symlinks exist
        expected_audio = os.path.join(dest_dir, "Test Series - S01E01.Reanimedia.mka")
        expected_sub = os.path.join(dest_dir, "Test Series - S01E01.rus.ass")
        assert not os.path.exists(expected_audio), "Audio symlink should not exist yet"
        assert not os.path.exists(expected_sub), "Subtitle symlink should not exist yet"
        print(f"✓ Verified no external media symlinks exist initially")
        
        # NOW: Simulate watcher detecting new external media files
        print(f"\n--- Simulating watcher event: external media added ---")
        
        # Re-create external media files
        with open(structure['audio'], 'w') as f:
            f.write("audio content")
        with open(structure['subtitle'], 'w') as f:
            f.write("subtitle content")
        print(f"✓ Created new external media files")
        
        # Watcher would trigger re-processing of the video
        # which should detect and link the new external media
        external_files = find_external_audio_and_subtitles(structure['video'])
        print(f"✓ Found {len(external_files)} external files after addition")
        
        assert len(external_files) == 2, f"Expected 2 external files, found {len(external_files)}"
        
        # Link them
        link_external_media(structure['video'], dest_video, external_files)
        print(f"✓ Linked external media")
        
        # Verify symlinks NOW exist
        assert os.path.islink(expected_audio), f"Audio symlink not created after watcher event"
        assert os.path.islink(expected_sub), f"Subtitle symlink not created after watcher event"
        assert os.path.exists(expected_audio), f"Audio symlink is broken"
        assert os.path.exists(expected_sub), f"Subtitle symlink is broken"
        
        print(f"\n✓ Verified symlinks created:")
        print(f"  - {os.path.basename(expected_audio)}")
        print(f"  - {os.path.basename(expected_sub)}")
        
        print("\n✅ Test 2 PASSED: External media added via watcher creates symlinks")
        
    finally:
        shutil.rmtree(test_dir)


def test_watcher_delete_external_media():
    """Test that deleting external media file triggers symlink removal."""
    print("\n=== Test 3: Watcher - Delete External Media ===\n")
    
    test_dir = tempfile.mkdtemp(prefix="ext_media_test_")
    
    try:
        # Setup: Everything already processed and linked
        structure = create_test_structure(test_dir)
        dest_dir = os.path.join(test_dir, "series", "Test Series (2024)", "Season 1")
        os.makedirs(dest_dir, exist_ok=True)
        
        dest_video = os.path.join(dest_dir, "Test Series - S01E01.mkv")
        os.symlink(
            os.path.relpath(structure['video'], dest_dir),
            dest_video
        )
        
        # Link external media
        external_files = find_external_audio_and_subtitles(structure['video'])
        link_external_media(structure['video'], dest_video, external_files)
        
        expected_audio = os.path.join(dest_dir, "Test Series - S01E01.Reanimedia.mka")
        expected_sub = os.path.join(dest_dir, "Test Series - S01E01.rus.ass")
        
        assert os.path.islink(expected_audio), "Audio symlink should exist initially"
        assert os.path.islink(expected_sub), "Subtitle symlink should exist initially"
        print(f"✓ Initial setup: video and external media symlinks exist")
        
        # NOW: Simulate watcher detecting deletion of external media
        print(f"\n--- Simulating watcher event: external media deleted ---")
        
        # Delete source audio file from mixed folder
        os.remove(structure['audio'])
        print(f"✓ Deleted audio file from mixed folder: {os.path.basename(structure['audio'])}")
        
        # Watcher would trigger cleanup_broken_links
        series_dest = os.path.join(test_dir, "series")
        movies_dest = os.path.join(test_dir, "movies")
        os.makedirs(movies_dest, exist_ok=True)
        
        removed = cleanup_broken_links(movies_dest, series_dest, structure['mixed'])
        print(f"✓ Cleanup removed {removed} broken link(s)")
        
        # Verify audio symlink is GONE
        assert not os.path.exists(expected_audio), f"Audio symlink should be removed (broken link)"
        print(f"✓ Verified audio symlink removed: {os.path.basename(expected_audio)}")
        
        # Verify subtitle symlink still exists (was not deleted)
        assert os.path.exists(expected_sub), f"Subtitle symlink should still exist"
        print(f"✓ Verified subtitle symlink still exists: {os.path.basename(expected_sub)}")
        
        # NOW: Delete subtitle too
        print(f"\n--- Deleting subtitle file ---")
        os.remove(structure['subtitle'])
        print(f"✓ Deleted subtitle file: {os.path.basename(structure['subtitle'])}")
        
        removed = cleanup_broken_links(movies_dest, series_dest, structure['mixed'])
        print(f"✓ Cleanup removed {removed} broken link(s)")
        
        # Verify subtitle symlink is GONE
        assert not os.path.exists(expected_sub), f"Subtitle symlink should be removed (broken link)"
        print(f"✓ Verified subtitle symlink removed: {os.path.basename(expected_sub)}")
        
        # Verify video symlink still exists
        assert os.path.exists(dest_video), f"Video symlink should still exist"
        print(f"✓ Verified video symlink still exists: {os.path.basename(dest_video)}")
        
        print("\n✅ Test 3 PASSED: External media deletion removes symlinks correctly")
        
    finally:
        shutil.rmtree(test_dir)


def test_orphaned_external_media_cleanup():
    """Test that orphaned external media (no matching video) is removed."""
    print("\n=== Test 4: Cleanup - Orphaned External Media ===\n")
    
    test_dir = tempfile.mkdtemp(prefix="ext_media_test_")
    
    try:
        # Setup: Everything linked
        structure = create_test_structure(test_dir)
        dest_dir = os.path.join(test_dir, "series", "Test Series (2024)", "Season 1")
        os.makedirs(dest_dir, exist_ok=True)
        
        dest_video = os.path.join(dest_dir, "Test Series - S01E01.mkv")
        os.symlink(
            os.path.relpath(structure['video'], dest_dir),
            dest_video
        )
        
        external_files = find_external_audio_and_subtitles(structure['video'])
        link_external_media(structure['video'], dest_video, external_files)
        
        expected_audio = os.path.join(dest_dir, "Test Series - S01E01.Reanimedia.mka")
        expected_sub = os.path.join(dest_dir, "Test Series - S01E01.rus.ass")
        
        print(f"✓ Initial setup: all symlinks exist")
        
        # NOW: Delete the VIDEO source file (making external media orphaned)
        print(f"\n--- Deleting video file (orphaning external media) ---")
        os.remove(structure['video'])
        print(f"✓ Deleted video file: {os.path.basename(structure['video'])}")
        
        # Run cleanup
        series_dest = os.path.join(test_dir, "series")
        movies_dest = os.path.join(test_dir, "movies")
        os.makedirs(movies_dest, exist_ok=True)
        
        removed = cleanup_broken_links(movies_dest, series_dest, structure['mixed'])
        print(f"✓ Cleanup removed {removed} item(s)")
        
        # Verify ALL symlinks are gone (video + external media)
        assert not os.path.exists(dest_video), f"Video symlink should be removed"
        assert not os.path.exists(expected_audio), f"Orphaned audio symlink should be removed"
        assert not os.path.exists(expected_sub), f"Orphaned subtitle symlink should be removed"
        
        print(f"✓ Verified all symlinks removed:")
        print(f"  - Video: {os.path.basename(dest_video)}")
        print(f"  - Audio: {os.path.basename(expected_audio)}")
        print(f"  - Subtitle: {os.path.basename(expected_sub)}")
        
        # Verify directory is empty or was removed by cleanup
        if os.path.exists(dest_dir):
            remaining = [f for f in os.listdir(dest_dir) if not f.endswith('.nfo')]
            assert len(remaining) == 0, f"Directory should be empty, found: {remaining}"
            print(f"✓ Verified destination directory cleaned up")
        else:
            print(f"✓ Verified destination directory was removed (empty cleanup)")
        
        print("\n✅ Test 4 PASSED: Orphaned external media cleaned up correctly")
        
    finally:
        shutil.rmtree(test_dir)


def test_external_media_with_multiple_videos():
    """Test external media handling when multiple videos exist in same folder."""
    print("\n=== Test 5: Multiple Videos - External Media Matching ===\n")
    
    test_dir = tempfile.mkdtemp(prefix="ext_media_test_")
    
    try:
        # Setup: Two episodes in same folder
        mixed = os.path.join(test_dir, "mixed")
        series_folder = os.path.join(mixed, "Test Series [2024]")
        os.makedirs(series_folder, exist_ok=True)
        
        # Episode 1
        video1 = os.path.join(series_folder, "[Group] Test Series - 01 [1080p].mkv")
        with open(video1, 'w') as f:
            f.write("video 1")
        
        # Episode 2
        video2 = os.path.join(series_folder, "[Group] Test Series - 02 [1080p].mkv")
        with open(video2, 'w') as f:
            f.write("video 2")
        
        # External media for episode 1 - MUST start with video filename (without extension)
        audio1 = os.path.join(series_folder, "[Group] Test Series - 01 [1080p].commentary.mka")
        with open(audio1, 'w') as f:
            f.write("audio 1")
        
        # External media for episode 2
        audio2 = os.path.join(series_folder, "[Group] Test Series - 02 [1080p].commentary.mka")
        with open(audio2, 'w') as f:
            f.write("audio 2")
        
        print(f"✓ Created 2 video files with matching external audio")
        
        # Process episode 1
        dest_dir = os.path.join(test_dir, "series", "Test Series (2024)", "Season 1")
        os.makedirs(dest_dir, exist_ok=True)
        
        dest_video1 = os.path.join(dest_dir, "Test Series - S01E01.mkv")
        os.symlink(os.path.relpath(video1, dest_dir), dest_video1)
        
        external1 = find_external_audio_and_subtitles(video1)
        print(f"\n✓ Episode 1: Found {len(external1.get('audio', []))} audio, {len(external1.get('subtitles', []))} subtitles")
        for src, name in external1.get('audio', []):
            print(f"    - Audio: {name}")
        for src, name in external1.get('subtitles', []):
            print(f"    - Subtitle: {name}")
        
        total1 = len(external1.get('audio', [])) + len(external1.get('subtitles', []))
        assert total1 == 1, f"Episode 1 should have 1 external file, found {total1}"
        assert audio1 in [src for src, _ in external1.get('audio', [])], f"Episode 1 should match only its audio"
        
        link_external_media(video1, dest_video1, external1)
        
        expected_audio1 = os.path.join(dest_dir, "Test Series - S01E01.commentary.mka")
        assert os.path.exists(expected_audio1), "Episode 1 audio symlink should exist"
        
        # Process episode 2
        dest_video2 = os.path.join(dest_dir, "Test Series - S01E02.mkv")
        os.symlink(os.path.relpath(video2, dest_dir), dest_video2)
        
        external2 = find_external_audio_and_subtitles(video2)
        print(f"✓ Episode 2: Found {len(external2.get('audio', []))} audio, {len(external2.get('subtitles', []))} subtitles")
        for src, name in external2.get('audio', []):
            print(f"    - Audio: {name}")
        
        total2 = len(external2.get('audio', [])) + len(external2.get('subtitles', []))
        assert total2 == 1, f"Episode 2 should have 1 external file, found {total2}"
        assert audio2 in [src for src, _ in external2.get('audio', [])], f"Episode 2 should match only its audio"
        
        link_external_media(video2, dest_video2, external2)
        
        expected_audio2 = os.path.join(dest_dir, "Test Series - S01E02.commentary.mka")
        assert os.path.exists(expected_audio2), "Episode 2 audio symlink should exist"
        
        print(f"\n✓ Both episodes have their own external audio symlinks")
        
        # Delete episode 1 video
        print(f"\n--- Deleting episode 1 video ---")
        os.remove(video1)
        
        series_dest = os.path.join(test_dir, "series")
        movies_dest = os.path.join(test_dir, "movies")
        os.makedirs(movies_dest, exist_ok=True)
        
        removed = cleanup_broken_links(movies_dest, series_dest, mixed)
        print(f"✓ Cleanup removed {removed} item(s)")
        
        # Episode 1 symlinks should be gone
        assert not os.path.exists(dest_video1), "Episode 1 video symlink should be removed"
        assert not os.path.exists(expected_audio1), "Episode 1 audio symlink should be removed"
        
        # Episode 2 symlinks should still exist
        assert os.path.exists(dest_video2), "Episode 2 video symlink should still exist"
        assert os.path.exists(expected_audio2), "Episode 2 audio symlink should still exist"
        
        print(f"✓ Episode 1 removed, Episode 2 intact")
        
        print("\n✅ Test 5 PASSED: Multiple videos handled correctly")
        
    finally:
        shutil.rmtree(test_dir)


if __name__ == "__main__":
    print("="*70)
    print("EXTERNAL MEDIA INTEGRATION TESTS")
    print("="*70)
    
    test_initial_scan_external_media()
    test_watcher_add_external_media()
    test_watcher_delete_external_media()
    test_orphaned_external_media_cleanup()
    test_external_media_with_multiple_videos()
    
    print("\n" + "="*70)
    print("✅ ALL TESTS PASSED!")
    print("="*70 + "\n")
