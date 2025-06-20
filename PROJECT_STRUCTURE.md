# Project Structure

This document outlines the directory structure for the Scene2Storyboard project.

## Root Directory

- `frontend/`: Contains the React/Vite frontend application.
- `backend/`: Contains the Python/FastAPI backend application.
- `README.md`: The main project README file.
- `PROJECT_STRUCTURE.md`: This file.
- `Scene2Storyboard.txt`: Implementation guide and technical documentation.

## Backend (`backend/`)

The backend is responsible for all video processing and AI tasks.

- `main.py`: The main FastAPI application file. It defines all API endpoints, orchestrates the processing pipeline, and handles CORS configuration.
- `requirements.txt`: A list of all Python dependencies for the backend.
- `venv/`: The Python virtual environment directory (gitignored).
- `uploads/`: A **temporary** directory where videos from direct uploads or YouTube downloads are stored before being processed and moved to a session folder. This folder should generally be empty.
- `scenes/`: The primary storage directory for all processed video data. Each sub-directory represents a single processing "session".
  - `[session_id]/`: A unique folder for each processed video. The name is generated from a timestamp and the video name.
    - `[video_file].mp4`: The original video file.
    - `[video_file].wav`: The extracted audio file for transcription.
    - `metadata.json`: A JSON file containing all information about the video, detected scenes, transcripts, and image captions.
    - `scenes/`: A subfolder containing all scene images for better organization (especially important for videos with many scenes).
      - `scene_001.jpg`, `scene_002.jpg`, ...: The representative frame images extracted for each detected scene.
- `utils/`: A package containing various utility modules for the backend.
  - `__init__.py`: Makes the `utils` directory a Python package.
  - `file_handler.py`: Contains the `FileHandler` class for managing file uploads and validation.
  - `youtube_handler.py`: Contains the `YouTubeHandler` class for downloading videos from YouTube using yt-dlp.
  - `scene_detector.py`: Contains the `SceneDetector` class, which uses `PySceneDetect` to find scene boundaries and extract frames.
  - `frame_extractor.py`: A utility for extracting metadata and frames from video files (some functionality may overlap or be used by `SceneDetector`).
  - `audio_transcriber.py`: Contains the `AudioTranscriber` class, which uses OpenAI's `Whisper` model to transcribe audio from video files.
  - `image_captioner.py`: Contains the `ImageCaptioner` class, which uses the BLIP model to generate descriptive captions for scene images.

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

## Current Implementation Status

### ✅ Completed Steps:

1. **Project Setup**: Backend and frontend structure, virtual environment, dependencies
2. **Video Input Handling**: File uploads and YouTube URL processing with yt-dlp
3. **Scene Detection**: OpenCV and PySceneDetect integration for frame extraction
4. **Audio Transcription**: Whisper model integration for speech-to-text
5. **Image Captioning**: BLIP model integration for visual scene descriptions

### 🔄 Next Steps:

6. **LLM Caption Enhancement**: Using open-source LLMs to create engaging comic-style captions
7. **Storyboard Generation**: Combining frames and captions into visual comic strips
8. **Frontend Integration**: React UI for uploading videos and displaying storyboards
