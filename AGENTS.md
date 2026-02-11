# Agent Rules & Project Standards

This file defines the rules and conventions for AI agents and developers working on the **metadata-fetcher** project. These rules are derived from the existing codebase and must be strictly followed.

## Project Overview
- **Purpose**: Automates media organization by scanning a "mixed" folder, identifying content using LLMs (OpenRouter), fetching metadata from TMDB, and creating organized symlinks with NFO files for Jellyfin.
- **Tech Stack**: Python 3.11, Docker, Docker Compose, OpenAI SDK (for LLM), Requests (for TMDB/Jellyfin APIs).
- **Key Directories**:
  - `src/`: Core application source code.
    - `src/clients/`: External API clients (LLM, TMDB, Jellyfin).
    - `src/core/`: Central logic, configuration, and processing orchestration.
    - `src/utils/`: Utility functions for filesystem, scanning, and NFO generation.
  - `media/`: Default volume mount points for media processing.
  - `.devcontainer/`: VS Code Dev Container configuration.

## Code Style
- **Naming**:
  - Functions and variables: `snake_case` (e.g., `setup_logging`, `processed_count`).
  - Classes: `PascalCase` (e.g., `LLMClient`, `TMDBClient`).
  - Constants: `UPPER_SNAKE_CASE` (e.g., `BASE_URL`).
- **Formatting**:
  - Use 4 spaces for indentation.
  - Include type hints for function parameters and return types where possible.
  - Use docstrings for complex functions.
- **Logging**:
  - Use the standard `logging` module.
  - Initialize loggers per module: `logger = logging.getLogger(__name__)`.
  - Log levels: `info` for progress, `warning` for missing data, `error` for failures.

## Architecture
- **Pattern**: Modular Client-based architecture.
  - `src/main.py`: Entry point of the application.
  - `src/core/processor.py`: Orchestrates the processing of individual media items.
  - `src/clients/`: Encapsulates external API interactions.
  - `src/utils/nfo_generator.py`: Handles XML generation for metadata.
  - `src/core/config.py`: Centralized configuration using `dataclasses` and `python-dotenv`.
- **Dependencies**: Keep `requirements.txt` minimal. Currently: `requests`, `python-dotenv`, `openai`.
- **Error Handling**: Use `try-except` blocks around I/O and API calls. Mark failed items in a `.failed` file within destination directories to avoid re-processing.

## Testing
- **Current State**: Comprehensive test suite in `tests/` directory with integration and end-to-end tests.
- **Test Files**:
  - `tests/test_external_media.py`: External audio/subtitle detection and renaming with suffix preservation.
  - `tests/test_watcher.py`: File system event detection for all supported formats (6 video, 6 audio, 5 subtitle).
  - `tests/test_external_media_integration.py`: Full integration - initial scan, add/delete, cleanup, multi-video scenarios.
  - `tests/test_watcher_external_media.py`: Real watcher behavior simulating external media addition and deletion events.
  - `tests/test_initial_scan_external_media.py`: Re-linking of external media during startup for already-processed files.
  - `tests/test_real_world_haibane.py`: Real-world Haibane Renmei structure (3 episodes, audio, subtitle folders).
  - `tests/test_complete_lifecycle.py`: End-to-end lifecycle test (download → initial scan → offline period → user adds subtitles → restart → re-link).
- **Coverage**: Relative symlinks, suffix preservation, correct multi-video matching, broken link cleanup, orphaned file removal.
- **Expectations**: New features should include corresponding tests. All 17 media formats supported.

## External Audio & Subtitle Support
- **Feature**: System automatically detects and symlinks external audio/subtitle files from mixed folder and its subdirectories.
- **Search Strategy**: Searches in video directory, sibling directories (parent's children), and subdirectories up to 5 levels deep for nested structures like `Series/Russian Subtitles [Group]/Inscriptions [ass]/`
- **Matching Logic**: External media filename must START with video filename (without extension). Suffixes preserved: `.Reanimedia`, `_inscriptions`, `.rus`, etc.
- **Key Functions**:
  - `find_external_audio_and_subtitles(video_src_path)` in `fs_utils.py`: Recursively searches for matching external media. Returns dict with `'audio'` and `'subtitles'` keys. Deduplicates results.
  - `link_external_media(video_src_path, video_dest_path, external_files)` in `fs_utils.py`: Creates relative symlinks with automatic filename renaming preserving suffixes.
  - `create_relative_symlink(src, dst)` in `fs_utils.py`: Creates portable relative symlinks (works when moved across mount points).
- **Processing Stages**:
  - **Initial Scan**: On startup, re-links external media for already-processed files (those with NFO). Catches external media added while app was offline.
  - **Watcher Events**: When external media is created, finds matching video and re-links all external media. When deleted, removes broken symlinks via cleanup.
- **Cleanup**: Two-stage process - first collects valid video files, then removes broken symlinks (any type) and orphaned external media files.

## Security
- **Secrets**:
  - **NEVER** hardcode API keys. Use `.env` files.
  - All configuration must be loaded via `src/core/config.py`.
  - `.env` is ignored by git; use `.env.example` for templates.
- **Input Validation**:
  - Sanitize filenames using `escape_filename` before creating filesystem entries.
  - Validate API responses before accessing nested keys (use `.get()`).
- **Common Pitfalls**:
  - Avoid absolute paths in symlinks; use `os.path.relpath` for portability.
  - Ensure `.ignore` files are respected during directory scans.

## Commits & PRs
- **Commits**: Follow [Conventional Commits](https://www.conventionalcommits.org/) (e.g., `feat:`, `fix:`, `docs:`, `chore:`).
- **Changelog**: No automated changelog generator is present; maintain clear commit messages.

## Deployment
- **Containerization**:
  - Use the provided `Dockerfile` (Python 3.11-slim).
  - Use `docker-compose.yml` for orchestration.
- **Environment Variables**:
  - Required: `LLM_API_KEY`, `TMDB_API_KEY`, `MIXED_PATH`, `MOVIES_DEST_PATH`, `SERIES_DEST_PATH`.
  - Optional: `LLM_MODEL`, `LLM_BASE_URL`, `JELLYFIN_URL`, `JELLYFIN_API_KEY`, `LOG_LEVEL`.
- **Build Process**: `docker compose build` followed by `docker compose up`.
- **Execution**: Run as a module: `python -m src.main`.

---
*Note: This file is a reference for AI agents. Do not modify these rules without explicit instruction.*
