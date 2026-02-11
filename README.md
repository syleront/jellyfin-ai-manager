# Metadata Fetcher

Automates media organization by scanning a "mixed" folder, identifying content using LLMs (OpenAI based api), fetching metadata from TMDB, and creating organized symlinks with NFO files for Jellyfin.

## Features

- **Initial Scan**: Automatically scans your mixed media directory on startup to process existing files.
- **Real-time Monitoring**: Runs as a daemon, watching for new files or deletions in real-time using `watchdog`.
- **Smart Batching**: Automatically groups files added to the same directory (e.g., during a torrent download) and processes them in batches after a 10-second quiet period to save LLM tokens.
- **Gap Protection**: Captures all file system events during the initial scan and processes them once the scan is complete, ensuring no data is lost.
- **Jellyfin Integration**: Automatically triggers library refreshes in Jellyfin after successful processing.
- **NFO Generation**: Creates Kodi/Jellyfin compatible `.nfo` files for movies, series, and episodes.
- **Broken Link Cleanup**: Automatically removes symlinks and NFO files when the source media is deleted.
- **External Audio & Subtitle Support**: Automatically detects and symlinks external audio tracks (.mka, .mp3, .aac, etc.) and subtitles (.ass, .srt, etc.) from sibling directories, making them available in Jellyfin alongside video files.

## Tech Stack

- **Python 3.11**
- **Docker & Docker Compose**
- **OpenRouter API** (for LLM-based media identification)
- **TMDB API** (for metadata)
- **Jellyfin API** (for library refreshes)
- **Watchdog** (for file system monitoring)

## Installation

1. Clone the repository.
2. Copy `.env.example` to `.env` and fill in your API keys and paths:
   ```bash
   cp .env.example .env
   ```
3. Configure your paths in `.env`:
   - `LLM_API_KEY`: Your OpenAI-compatible API key (OpenRouter, Perplexity, etc.).
   - `TMDB_API_KEY`: Your TMDB API key.
   - `MIXED_PATH`: Path inside the container where mixed media is located.
   - `MOVIES_DEST_PATH`: Path inside the container for organized movies.
   - `SERIES_DEST_PATH`: Path inside the container for organized series.
   - `JELLYFIN_URL` & `JELLYFIN_API_KEY`: (Optional) For library refreshes.

## Usage

### Docker Compose (Recommended)

Build and start the daemon:
```bash
docker compose build
docker compose up -d
```

### Manual Execution

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Run the application:
   ```bash
   python -m src.main
   ```

## Project Structure

- `src/main.py`: Entry point, orchestrates initial scan and watcher startup.
- `src/core/watcher.py`: Real-time file system monitoring and batching logic.
- `src/core/processor.py`: Core logic for processing movies and series.
- `src/clients/`: API clients for LLM, TMDB, and Jellyfin.
- `src/utils/`: Utility functions for filesystem operations, scanning, and NFO generation.

## How it Works

1. **Startup**: The application starts the `Watcher` to begin capturing file system events.
2. **Cleanup & Re-linking**: Removes broken links from previous sessions, then re-links external media for already-processed files (important when external media was added while app was offline).
3. **Initial Scan**: Performs a full recursive scan of `MIXED_PATH`, identifying and processing any new files not already in destination folders.
4. **Event Processing**: Once the initial scan is done, begins processing events captured by the `Watcher`.
5. **Batching**: If multiple files are added to a folder (like a new season), waits for a 10-second pause before sending the whole batch to the LLM for identification.
6. **Metadata & Symlinks**: For each identified item, fetches details from TMDB, creates a relative symlink in the appropriate destination folder, and generates `.nfo` files.
7. **External Media Linking**: After creating video symlinks, searches for matching external audio tracks and subtitles (in video dir, sibling dirs, and subdirs) and creates symlinks with Jellyfin-compatible names. Preserves naming suffixes.
8. **Real-time External Media**: When external media files are added during runtime, the watcher detects them, finds the matching video, and automatically creates the symlinks.
9. **Cleanup**: When a file is deleted, removes corresponding symlinks, NFO files, and associated external media symlinks from destination.

## External Audio & Subtitle Support

The application automatically detects and links external audio tracks and subtitles from the mixed folder and its subdirectories, making them available in Jellyfin with proper naming and labeling.

### Supported Formats
- **Audio**: `.mka`, `.mp3`, `.aac`, `.ac3`, `.dts`, `.flac`
- **Subtitles**: `.ass`, `.srt`, `.ssa`, `.sub`, `.vtt`

### How It Works

When processing a video file, the system searches for matching external media files in:
1. **Same directory** as the video
2. **Sibling directories** (brother folders at the same level as video)
3. **Subdirectories** up to 5 levels deep (for nested structures like `Series/Language/Quality/file.ass`)

Matching is based on filename prefix: external media filename must start with video filename. For example, with video `[ANK-Raws] Haibane Renmei - 01 (BDrip 1920x1080).mkv`, these match:
- `[ANK-Raws] Haibane Renmei - 01 (BDrip 1920x1080).Reanimedia.mka` ✓ (audio)
- `[ANK-Raws] Haibane Renmei - 01 (BDrip 1920x1080).Reanimedia_inscriptions.ass` ✓ (subtitle)
- But `[ANK-Raws] Haibane Renmei - 02 (...).mka` ✗ (different episode)

### Processing Timing

External media is handled in two ways:

**Initial Scan** (on app startup):
- Processes new videos and links their external media
- **Also re-links external media for already-processed videos** (files with NFO), catching media added while app was offline

**Real-time** (during app runtime):
- When new external media files are created, watcher automatically detects them, finds the matching video, and creates symlinks
- When external media files are deleted, broken symlinks are cleaned up automatically

**Source structure:**
```
[ANK-Raws] Haibane Renmei (BDrip 1920x1080 x264 FLAC Hi10P)/
├── Russian Sound [Reanimedia]/
│   ├── [ANK-Raws] Haibane Renmei - 01 (BDrip 1920x1080 x264 FLAC Hi10P).Reanimedia.mka
│   └── [ANK-Raws] Haibane Renmei - 02 (BDrip 1920x1080 x264 FLAC Hi10P).Reanimedia.mka
├── Russian Subtitles [Reanimedia]/
│   ├── Fonts/
│   ├── Full [ass]/
│   └── Inscriptions [ass]/
│       ├── [ANK-Raws] Haibane Renmei - 01 (BDrip 1920x1080 x264 FLAC Hi10P).Reanimedia_inscriptions.ass
│       ├── [ANK-Raws] Haibane Renmei - 02 (BDrip 1920x1080 x264 FLAC Hi10P).Reanimedia_inscriptions.ass
├── [ANK-Raws] Haibane Renmei - 01 (BDrip 1920x1080 x264 FLAC Hi10P).mkv
└── [ANK-Raws] Haibane Renmei - 02 (BDrip 1920x1080 x264 FLAC Hi10P).mkv
```

**Destination structure** (after linking):
```
Haibane Renmei (2002)/Season 1/
├── Haibane Renmei - S01E01.mkv (symlink to source)
├── Haibane Renmei - S01E01.Reanimedia.mka (symlink to audio, preserves suffix)
├── Haibane Renmei - S01E01.Reanimedia_inscriptions.ass (symlink to subtitle, preserves suffix)
├── Haibane Renmei - S01E02.mkv (symlink to source)
├── Haibane Renmei - S01E02.Reanimedia.mka (symlink to audio)
└── Haibane Renmei - S01E02.Reanimedia_inscriptions.ass (symlink to subtitle)
```

All symlinks use **relative paths** for portability, so they work correctly even when moved to different mount points or systems. Suffixes like `.Reanimedia` and `_inscriptions` are preserved in destination names, allowing Jellyfin to properly identify and label audio tracks and subtitle versions.

## License

MIT
