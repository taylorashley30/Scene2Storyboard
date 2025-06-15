from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
import os
from typing import Optional
from pydantic import BaseModel
from utils.file_handler import FileHandler
from utils.youtube_handler import YouTubeHandler

# Initialize FastAPI app
app = FastAPI(
    title="Scene2Storyboard API",
    description="API for converting videos to comic strip-style storyboards",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # React dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create uploads directory if it doesn't exist
UPLOADS_DIR = "uploads"
os.makedirs(UPLOADS_DIR, exist_ok=True)

# Initialize handlers
file_handler = FileHandler()
youtube_handler = YouTubeHandler()

# Models
class VideoInput(BaseModel):
    youtube_url: Optional[str] = None

# Health check endpoint
@app.get("/health")
async def health_check():
    return {"status": "healthy"}

# Video processing endpoint for file upload
@app.post("/process/upload")
async def process_video_upload(file: UploadFile = File(...)):
    try:
        # Validate file
        if not file_handler.is_valid_video_file(file.filename):
            raise HTTPException(status_code=400, detail="Invalid video file format")

        # Save file
        file_path = await file_handler.save_upload_file(file)
        
        # TODO: Implement video processing logic
        return {
            "message": "Video uploaded successfully",
            "file_path": file_path,
            "status": "success"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Video processing endpoint for YouTube URL
@app.post("/process/youtube")
async def process_youtube_video(video_input: VideoInput):
    try:
        if not video_input.youtube_url:
            raise HTTPException(status_code=400, detail="YouTube URL is required")

        # Validate YouTube URL
        if not youtube_handler.is_valid_youtube_url(video_input.youtube_url):
            raise HTTPException(status_code=400, detail="Invalid YouTube URL")

        # Download video
        file_path = youtube_handler.download_video(video_input.youtube_url)
        
        # TODO: Implement video processing logic
        return {
            "message": "YouTube video downloaded successfully",
            "file_path": file_path,
            "status": "success"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Error handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    return JSONResponse(
        status_code=500,
        content={"message": "Internal server error", "detail": str(exc)},
    )

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True) 