# Project Structure

This document outlines the directory structure for the Scene2Storyboard project.

## Root Directory

- `frontend/`: Contains the React/Vite frontend application.
- `backend/`: Contains the Python/FastAPI backend application.
- `README.md`: The main project README file.
- `PROJECT_STRUCTURE.md`: This file.

## Backend (`backend/`)

The backend is responsible for all video processing and AI tasks.

- `main.py`: The main FastAPI application file. It defines all API endpoints, orchestrates the processing pipeline, and handles CORS configuration.
- `requirements.txt`: A list of all Python dependencies for the backend.
- `venv/`: The Python virtual environment directory (gitignored).
- `uploads/`: A **temporary** directory where videos from direct uploads or YouTube downloads are stored before being processed and moved to a session folder. This folder should generally be empty.
- `scenes/`: The primary storage directory for all processed video data. Each sub-directory represents a single processing "session".
  - `[session_id]/`: A unique folder for each processed video. The name is generated from a timestamp and the video name.
    - `[video_file].mp4`: The original video file.
    - `metadata.json`: A JSON file containing all information about the video, detected scenes, and transcripts.
    - `scene_001.jpg`, `scene_002.jpg`, ...: The representative frame images extracted for each detected scene.
- `utils/`: A package containing various utility modules for the backend.
  - `__init__.py`: Makes the `utils` directory a Python package.
  - `file_handler.py`: Contains the `FileHandler` class for managing file uploads and validation.
  - `youtube_handler.py`: Contains the `YouTubeHandler` class for downloading videos from YouTube.
  - `scene_detector.py`: Contains the `SceneDetector` class, which uses `PySceneDetect` to find scene boundaries and extract frames.
  - `frame_extractor.py`: A utility for extracting metadata and frames from video files (some functionality may overlap or be used by `SceneDetector`).
  - `audio_transcriber.py`: Contains the `AudioTranscriber` class, which uses OpenAI's `Whisper` model to transcribe audio from video files.

## Frontend (`frontend/`)

The frontend is a standard React + TypeScript application created with Vite.

- `index.html`: The main HTML entry point.
- `src/`: The main source code directory.
  - `main.tsx`: The main application entry point.
  - `App.tsx`: The root React component.
- `public/`: Static assets.
- `package.json`: Project dependencies and scripts.
- `vite.config.ts`: Vite configuration.
- `tsconfig.json`: TypeScript configuration.
