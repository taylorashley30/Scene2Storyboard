# Scene2Storyboard

Scene2Storyboard is an AI-powered application that converts videos into comic strip-style storyboards. It uses multimodal AI (vision + audio + text) to analyze videos, extract key scenes, generate captions, and create engaging storyboards.

## Features

- Video input via file upload, YouTube URL, or Instagram URL (posts, reels)
- Automatic scene detection using OpenCV
- Audio transcription using Whisper
- Image captioning using BLIP
- Optional LLM caption enhancement (Gemini API via `GEMINI_API_KEY` when set; else rule-based only)
- Comic strip-style storyboard generation
- Modern React frontend with TypeScript

## Tech Stack

### Backend

- Python with FastAPI
- OpenCV for scene detection
- Whisper for audio transcription
- BLIP for image captioning
- Optional Gemini API for caption enhancement (or use rule-based; see Scene2Storyboard.txt for local Mistral/TinyLlama)
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

## Optional: LLM caption enhancement (Gemini, free tier)

For cleaner storyboard captions (fixing Whisper mishearings and formatting) **without paid usage**, you can enable optional LLM enhancement using **Gemini via Google AI Studio**:

1. Go to `https://aistudio.google.com` and sign in with your Google account.
2. Accept the terms, then click **“Get API key” → “Create API key”** and choose a project/region.
3. Copy your API key.
4. In `backend/`, copy `.env.example` to `.env` (if you haven’t already) and set:
   ```env
   GEMINI_API_KEY=your_gemini_key_here
   ```
5. Restart the backend. Caption enhancement will use Gemini (e.g. `gemini-1.5-flash`) in a **single batch request per video**, with conservative scene caps to respect free-tier rate limits; otherwise it falls back to the built-in rule-based enhancer.

If you prefer **no external API at all**, you can leave `GEMINI_API_KEY` unset and only use the rule-based enhancer. The project guide `Scene2Storyboard.txt` also describes using a local model (Mistral/TinyLlama) for caption enhancement; that path can be added in a future update.

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
4. Upload a video or provide a YouTube or Instagram URL
5. Wait for processing and view your generated storyboard

### Instagram notes

Instagram URLs (posts, reels) are supported via yt-dlp. If a download fails with "login required" or "content not available," Instagram may be blocking unauthenticated access. You can try using cookies (e.g. `--cookies-from-browser` in yt-dlp) by extending the handler if needed.

## License

This project is open source and available under the MIT License.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
