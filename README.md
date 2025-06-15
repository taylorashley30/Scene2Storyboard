# Scene2Storyboard

Scene2Storyboard is an AI-powered application that converts videos into comic strip-style storyboards. It uses multimodal AI (vision + audio + text) to analyze videos, extract key scenes, generate captions, and create engaging storyboards.

## Features

- Video input via file upload or YouTube URL
- Automatic scene detection using OpenCV
- Audio transcription using Whisper
- Image captioning using BLIP
- Caption enhancement using Mistral/TinyLlama
- Comic strip-style storyboard generation
- Modern React frontend with TypeScript

## Tech Stack

### Backend

- Python with FastAPI
- OpenCV for scene detection
- Whisper for audio transcription
- BLIP for image captioning
- Mistral/TinyLlama for caption enhancement
- PySceneDetect for advanced scene detection

### Frontend

- React with TypeScript
- Vite for build tooling
- Modern UI components

## Setup Instructions

### Backend Setup

1. Navigate to the backend directory:
   ```bash
   cd backend
   ```
2. Create and activate virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

### Frontend Setup

1. Navigate to the frontend directory:
   ```bash
   cd frontend
   ```
2. Install dependencies:
   ```bash
   npm install
   ```
3. Start development server:
   ```bash
   npm run dev
   ```

## Usage

1. Start the backend server:
   ```bash
   cd backend
   uvicorn main:app --reload
   ```
2. Start the frontend development server:
   ```bash
   cd frontend
   npm run dev
   ```
3. Open your browser and navigate to `http://localhost:5173`
4. Upload a video or provide a YouTube URL
5. Wait for processing and view your generated storyboard

## License

This project is open source and available under the MIT License.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
