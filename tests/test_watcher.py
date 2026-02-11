#!/usr/bin/env python3
"""
Test script for watcher functionality.
Tests event detection for video, audio, and subtitle files.
"""

import os
import sys
import tempfile
import shutil
import time
import threading
from pathlib import Path

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.core.watcher import MediaWatcherHandler


class MockConfig:
    """Mock config for testing."""
    def __init__(self, mixed_path):
        self.mixed_path = mixed_path
        self.movies_dest_path = os.path.join(mixed_path, "movies")
        self.series_dest_path = os.path.join(mixed_path, "series")
        self.jellyfin_movies_library_id = None
        self.jellyfin_series_library_id = None


class MockLLM:
    """Mock LLM client."""
    pass


class MockProcessor:
    """Mock processor."""
    pass


class MockJellyfin:
    """Mock Jellyfin client."""
    pass


def test_watcher_extensions():
    """Test that watcher recognizes correct file extensions."""
    print("\n=== Testing Watcher Extension Recognition ===\n")
    
    config = MockConfig(tempfile.gettempdir())
    handler = MediaWatcherHandler(config, MockLLM(), MockProcessor(), MockJellyfin())
    
    # Test video extensions
    print("Video extensions:")
    for ext in handler.video_extensions:
        print(f"  {ext}")
    
    expected_video = ('.mkv', '.mp4', '.avi', '.mov', '.m4v', '.m2ts')
    assert handler.video_extensions == expected_video, "Video extensions mismatch"
    print("  ✓ Video extensions correct\n")
    
    # Test audio extensions
    print("Audio extensions:")
    for ext in handler.audio_extensions:
        print(f"  {ext}")
    
    expected_audio = ('.mka', '.mp3', '.aac', '.ac3', '.dts', '.flac')
    assert handler.audio_extensions == expected_audio, "Audio extensions mismatch"
    print("  ✓ Audio extensions correct\n")
    
    # Test subtitle extensions
    print("Subtitle extensions:")
    for ext in handler.subtitle_extensions:
        print(f"  {ext}")
    
    expected_subs = ('.ass', '.srt', '.ssa', '.sub', '.vtt')
    assert handler.subtitle_extensions == expected_subs, "Subtitle extensions mismatch"
    print("  ✓ Subtitle extensions correct\n")
    
    # Test external media extensions
    print("External media extensions (audio + subtitles):")
    print(f"  Total: {len(handler.external_media_extensions)} formats")
    print("  ✓ External media extensions created\n")


def test_event_detection():
    """Test that on_created detects different file types."""
    print("\n=== Testing Event Detection ===\n")
    
    test_dir = tempfile.mkdtemp(prefix="watcher_test_")
    config = MockConfig(test_dir)
    handler = MediaWatcherHandler(config, MockLLM(), MockProcessor(), MockJellyfin())
    
    try:
        # Create test files
        test_cases = [
            ("video.mkv", "video", True),
            ("video.mp4", "video", True),
            ("audio.mka", "audio", False),
            ("audio.mp3", "audio", False),
            ("subtitle.ass", "subtitle", False),
            ("subtitle.srt", "subtitle", False),
            ("random.txt", "other", False),
        ]
        
        print("Test cases:")
        for filename, type_name, should_batch in test_cases:
            file_path = os.path.join(test_dir, filename)
            with open(file_path, 'w') as f:
                f.write("test")
            
            # Create mock event
            class MockEvent:
                def __init__(self, path):
                    self.src_path = path
                    self.dest_path = path
                    self.is_directory = False
            
            event = MockEvent(file_path)
            
            initial_pending = len(handler.pending_batches)
            handler.on_created(event)
            final_pending = len(handler.pending_batches)
            
            batched = final_pending > initial_pending
            
            status = "✓" if batched == should_batch else "✗"
            action = "queued for batching" if batched else "logged but not queued"
            print(f"  {status} {filename:20} ({type_name:10}): {action}")
            
            assert batched == should_batch, f"Unexpected behavior for {filename}"
            
            # Clean up pending batches
            handler.pending_batches.clear()
        
        print("\n  ✓ All event detection tests passed")
        
    finally:
        shutil.rmtree(test_dir)


def test_deletion_events():
    """Test that deletion events are captured for all file types."""
    print("\n=== Testing Deletion Event Handling ===\n")
    
    test_dir = tempfile.mkdtemp(prefix="watcher_test_")
    config = MockConfig(test_dir)
    handler = MediaWatcherHandler(config, MockLLM(), MockProcessor(), MockJellyfin())
    
    try:
        test_files = [
            "video.mkv",
            "audio.mka",
            "subtitle.ass",
        ]
        
        print("Deletion events:")
        for filename in test_files:
            file_path = os.path.join(test_dir, filename)
            with open(file_path, 'w') as f:
                f.write("test")
            
            class MockEvent:
                def __init__(self, path):
                    self.src_path = path
                    self.is_directory = False
            
            event = MockEvent(file_path)
            
            initial_queue_size = handler.event_queue.qsize()
            handler.on_deleted(event)
            final_queue_size = handler.event_queue.qsize()
            
            assert final_queue_size > initial_queue_size, f"Deletion event not queued for {filename}"
            
            # Get the event
            event_type, data = handler.event_queue.get_nowait()
            assert event_type == 'deleted', f"Wrong event type for {filename}"
            assert data == file_path, f"Wrong file path in event for {filename}"
            
            print(f"  ✓ {filename:20}: deletion event captured")
        
        print("\n  ✓ All deletion event tests passed")
        
    finally:
        shutil.rmtree(test_dir)


def test_batching_timeout():
    """Test that batch timeout works correctly."""
    print("\n=== Testing Batch Timeout ===\n")
    
    test_dir = tempfile.mkdtemp(prefix="watcher_test_")
    config = MockConfig(test_dir)
    handler = MediaWatcherHandler(config, MockLLM(), MockProcessor(), MockJellyfin())
    handler.batch_timeout = 0.5  # Short timeout for testing
    
    try:
        # Create a video file
        video_path = os.path.join(test_dir, "video.mkv")
        with open(video_path, 'w') as f:
            f.write("test")
        
        class MockEvent:
            def __init__(self, path):
                self.src_path = path
                self.dest_path = path
                self.is_directory = False
        
        event = MockEvent(video_path)
        
        print("Testing batch timeout (0.5s):")
        print(f"  Queue empty: {handler.event_queue.empty()}")
        
        # Queue a file
        handler.on_created(event)
        print(f"  File queued for batching")
        print(f"  Waiting for batch timeout...")
        
        # Wait for batch timeout
        time.sleep(1.0)
        
        print(f"  Queue has events: {not handler.event_queue.empty()}")
        
        if not handler.event_queue.empty():
            event_type, data = handler.event_queue.get_nowait()
            print(f"  Event type: {event_type}")
            assert event_type == 'batch_created', f"Wrong event type: {event_type}"
            folder_path, files = data
            print(f"  Files in batch: {len(files)}")
            assert len(files) == 1, f"Wrong number of files in batch: {len(files)}"
            assert video_path in files, f"Video not in batch"
            print(f"  ✓ Batch timeout working correctly")
        else:
            print(f"  ✗ Batch event not queued after timeout")
            assert False, "Batch timeout failed"
        
    finally:
        shutil.rmtree(test_dir)


if __name__ == "__main__":
    test_watcher_extensions()
    test_event_detection()
    test_deletion_events()
    test_batching_timeout()
    
    print("\n" + "="*50)
    print("✓ All watcher tests passed successfully!")
    print("="*50 + "\n")
