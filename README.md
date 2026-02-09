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
2. **Initial Scan**: It performs a full recursive scan of the `MIXED_PATH`, identifying and processing any files not already in the destination folders.
3. **Event Processing**: Once the initial scan is done, it begins processing events captured by the `Watcher`.
4. **Batching**: If multiple files are added to a folder (like a new season of a show), it waits for a 10-second pause in activity before sending the whole batch to the LLM for identification.
5. **Metadata & Symlinks**: For each identified item, it fetches details from TMDB, creates a relative symlink in the appropriate destination folder, and generates `.nfo` files.
6. **Cleanup**: If a file is deleted from the mixed folder, the daemon detects this and removes the corresponding symlink and NFO file from the destination.

## License

MIT
