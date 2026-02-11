#!/usr/bin/env python3
"""
Complete end-to-end test: Initial scan → user adds subtitles → app restarts → initial scan again.
This reproduces the exact user scenario.
"""

import os
import sys
import tempfile
import shutil

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.utils.fs_utils import create_relative_symlink, find_external_audio_and_subtitles, link_external_media, get_processed_files


def test_complete_lifecycle():
    """
    Complete lifecycle test:
    1. Initial scan processes videos with audio
    2. App shuts down
    3. User adds subtitle folder
    4. App restarts and runs initial scan
    5. Subtitles should be linked automatically
    """
    print("\n" + "="*70)
    print("COMPLETE LIFECYCLE TEST")
    print("="*70 + "\n")
    
    test_dir = tempfile.mkdtemp(prefix="lifecycle_test_")
    
    try:
        mixed_path = os.path.join(test_dir, "mixed")
        movies_dest = os.path.join(test_dir, "movies")
        series_dest = os.path.join(test_dir, "series")
        os.makedirs(mixed_path, exist_ok=True)
        os.makedirs(movies_dest, exist_ok=True)
        os.makedirs(series_dest, exist_ok=True)
        
        # ========== PHASE 1: Initial Setup ==========
        print("PHASE 1: User downloads torrent (video + audio only)")
        print("-" * 70)
        
        series_folder = os.path.join(mixed_path, "[ANK-Raws] Haibane Renmei (BDrip 1920x1080 x264 FLAC Hi10P)")
        os.makedirs(series_folder, exist_ok=True)
        
        # Create 3 episodes
        videos = []
        for i in range(1, 4):
            video = os.path.join(series_folder, f"[ANK-Raws] Haibane Renmei - {i:02d} (BDrip 1920x1080 x264 FLAC Hi10P).mkv")
            with open(video, 'w') as f:
                f.write(f"video {i}")
            videos.append(video)
        
        # Create audio folder
        audio_folder = os.path.join(series_folder, "Russian Sound [Reanimedia]")
        os.makedirs(audio_folder, exist_ok=True)
        
        audios = []
        for i in range(1, 4):
            audio = os.path.join(audio_folder, f"[ANK-Raws] Haibane Renmei - {i:02d} (BDrip 1920x1080 x264 FLAC Hi10P).Reanimedia.mka")
            with open(audio, 'w') as f:
                f.write(f"audio {i}")
            audios.append(audio)
        
        print(f"  ✓ Created {len(videos)} video files")
        print(f"  ✓ Created {len(audios)} audio files")
        
        # ========== PHASE 2: First Initial Scan ==========
        print("\nPHASE 2: App starts and runs initial scan")
        print("-" * 70)
        
        dest_dir = os.path.join(series_dest, "Haibane Renmei (2002)", "Season 1")
        os.makedirs(dest_dir, exist_ok=True)
        
        # Simulate processor.process_series() for each video
        for i, video_src in enumerate(videos, 1):
            dest_video = os.path.join(dest_dir, f"Haibane Renmei - S01E{i:02d}.mkv")
            create_relative_symlink(video_src, dest_video)
            
            # Create NFO
            nfo_path = os.path.join(dest_dir, f"Haibane Renmei - S01E{i:02d}.nfo")
            with open(nfo_path, 'w') as f:
                f.write("<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n<episodedetails>\n</episodedetails>")
            
            # Link external media (only audio at this point)
            external = find_external_audio_and_subtitles(video_src)
            link_external_media(video_src, dest_video, external)
            
            print(f"  ✓ Episode {i}: Processed (video + {len(external['audio'])} audio)")
        
        # Verify state after first scan
        for i in range(1, 4):
            expected_audio = os.path.join(dest_dir, f"Haibane Renmei - S01E{i:02d}.Reanimedia.mka")
            expected_sub = os.path.join(dest_dir, f"Haibane Renmei - S01E{i:02d}.Reanimedia_inscriptions.ass")
            
            assert os.path.exists(expected_audio), f"Episode {i} audio should exist"
            assert not os.path.exists(expected_sub), f"Episode {i} subtitle should NOT exist"
        
        print(f"\n  ✓ All episodes processed, audio linked, no subtitles yet")
        
        # ========== PHASE 3: App Shutdown + User Adds Subtitles ==========
        print("\nPHASE 3: App shuts down, user adds subtitle folder")
        print("-" * 70)
        
        subs_base = os.path.join(series_folder, "Russian Subtitles [Reanimedia]")
        subs_folder = os.path.join(subs_base, "Inscriptions [ass]")
        os.makedirs(subs_folder, exist_ok=True)
        
        subs = []
        for i in range(1, 4):
            sub = os.path.join(subs_folder, f"[ANK-Raws] Haibane Renmei - {i:02d} (BDrip 1920x1080 x264 FLAC Hi10P).Reanimedia_inscriptions.ass")
            with open(sub, 'w') as f:
                f.write(f"subtitle {i}")
            subs.append(sub)
        
        print(f"  ✓ User added {len(subs)} subtitle files")
        
        # Verify subtitles not linked yet
        for i in range(1, 4):
            expected_sub = os.path.join(dest_dir, f"Haibane Renmei - S01E{i:02d}.Reanimedia_inscriptions.ass")
            assert not os.path.exists(expected_sub), f"Episode {i} subtitle should NOT be linked yet"
        
        print(f"  ✓ Subtitles not linked yet (app was offline)")
        
        # ========== PHASE 4: App Restarts and Runs Initial Scan ==========
        print("\nPHASE 4: App restarts and runs initial scan (re-linking)")
        print("-" * 70)
        
        # Get processed files
        processed_files = get_processed_files(movies_dest, series_dest)
        print(f"  ✓ Found {len(processed_files)} already processed files")
        
        # Re-link external media for already processed files
        # (This is what we added to src/main.py)
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
                            # Resolve symlink
                            link_target = os.readlink(dest_video_path)
                            if not os.path.isabs(link_target):
                                link_target = os.path.normpath(os.path.join(root, link_target))
                            
                            src_video_path = os.path.abspath(link_target)
                            if os.path.exists(src_video_path):
                                # Re-link external media
                                external_files = find_external_audio_and_subtitles(src_video_path)
                                if external_files['audio'] or external_files['subtitles']:
                                    linked = link_external_media(src_video_path, dest_video_path, external_files)
                                    if linked > 0:
                                        relinked_count += linked
        
        print(f"  ✓ Re-linked {relinked_count} external media files")
        
        # ========== PHASE 5: Verification ==========
        print("\nPHASE 5: Verifying final state")
        print("-" * 70)
        
        for i in range(1, 4):
            expected_video = os.path.join(dest_dir, f"Haibane Renmei - S01E{i:02d}.mkv")
            expected_audio = os.path.join(dest_dir, f"Haibane Renmei - S01E{i:02d}.Reanimedia.mka")
            expected_sub = os.path.join(dest_dir, f"Haibane Renmei - S01E{i:02d}.Reanimedia_inscriptions.ass")
            
            assert os.path.exists(expected_video), f"Episode {i} video should exist"
            assert os.path.exists(expected_audio), f"Episode {i} audio should exist"
            assert os.path.exists(expected_sub), f"Episode {i} subtitle should exist NOW"
            assert os.path.islink(expected_sub), f"Episode {i} subtitle should be a symlink"
            
            print(f"  ✓ Episode {i}: video ✓ audio ✓ subtitle ✓")
        
        print("\n" + "="*70)
        print("✅ COMPLETE LIFECYCLE TEST PASSED!")
        print("="*70)
        print("\nSummary:")
        print("  • Phase 1: User downloads torrent (video + audio)")
        print("  • Phase 2: Initial scan processes and links audio")
        print("  • Phase 3: User adds subtitle folder while app offline")
        print("  • Phase 4: App restarts, initial scan re-links all external media")
        print("  • Phase 5: All subtitles now linked correctly")
        print("="*70 + "\n")
        
    finally:
        shutil.rmtree(test_dir)


if __name__ == "__main__":
    test_complete_lifecycle()
