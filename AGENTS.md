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
- **Current State**: No formal testing framework (pytest/unittest) is currently implemented.
- **Expectations**:
  - When adding new features, prioritize manual verification of symlink creation and NFO validity.
  - If a testing framework is added, it should be `pytest`.
  - Add tests for utility functions like `escape_filename` or XML generation logic.

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
  - Required: `OPENROUTER_API_KEY`, `TMDB_API_KEY`, `MIXED_PATH`, `MOVIES_DEST_PATH`, `SERIES_DEST_PATH`.
  - Optional: `JELLYFIN_URL`, `JELLYFIN_API_KEY`, `LOG_LEVEL`.
- **Build Process**: `docker compose build` followed by `docker compose up`.
- **Execution**: Run as a module: `python -m src.main`.

---
*Note: This file is a reference for AI agents. Do not modify these rules without explicit instruction.*
