#!/usr/bin/env python3
"""
Scene2Storyboard Backend API
Main FastAPI application for video processing and storyboard generation
"""

import os
import shutil
from typing import Optional
from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel

# Import utility modules
from utils.file_handler import FileHandler
from utils.youtube_handler import YouTubeHandler
from utils.scene_detector import SceneDetector
from utils.audio_transcriber import AudioTranscriber
from utils.image_captioner import ImageCaptioner
from utils.caption_enhancer import CaptionEnhancer
from utils.storyboard_generator import StoryboardGenerator

# Initialize FastAPI app
app = FastAPI(title="Scene2Storyboard API", version="1.0.0")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],  # React dev servers
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize utility classes
file_handler = FileHandler()
youtube_handler = YouTubeHandler()
scene_detector = SceneDetector()
audio_transcriber = AudioTranscriber()
image_captioner = ImageCaptioner()
caption_enhancer = CaptionEnhancer()
storyboard_generator = StoryboardGenerator()

# Configuration
SCENES_DIR = "scenes"
os.makedirs(SCENES_DIR, exist_ok=True)

# Pydantic models
class VideoInput(BaseModel):
    youtube_url: Optional[str] = None

class SceneDetectionRequest(BaseModel):
    use_pyscenedetect: bool = True
    video_name: Optional[str] = None

# Health check endpoint
@app.get("/health")
async def health_check():
    return {"status": "healthy"}

# Video processing endpoint for file upload
@app.post("/process/upload")
async def process_video_upload(
    file: UploadFile = File(...),
    use_pyscenedetect: bool = Form(True),
    video_name: Optional[str] = Form(None)
):
    try:
        # Validate file
        if not file_handler.is_valid_video_file(file.filename):
            raise HTTPException(status_code=400, detail="Invalid video file format")

        # Save file to a temporary location
        temp_video_path = await file_handler.save_upload_file(file)
        
        # Process video for scene detection, which creates the session folder
        scene_metadata = scene_detector.process_video(
            video_path=temp_video_path,
            video_name=video_name or file.filename,
            use_pyscenedetect=use_pyscenedetect
        )
        session_path = scene_metadata["session_path"]
        
        # Move the video file into its session folder
        final_video_filename = os.path.basename(temp_video_path)
        final_video_path = os.path.join(session_path, final_video_filename)
        shutil.move(temp_video_path, final_video_path)
        
        # Update metadata with the new, final path
        scene_metadata["video_path"] = final_video_path
        
        # Get scene transcripts using the final video path
        scene_timestamps = [(scene["start_time"], scene["end_time"]) for scene in scene_metadata["scenes"]]
        scene_transcripts = audio_transcriber.get_scene_transcripts(final_video_path, scene_timestamps)
        
        # Add transcripts to scene metadata
        for scene, transcript in zip(scene_metadata["scenes"], scene_transcripts):
            scene["transcript"] = transcript
            # Generate image caption for each scene frame
            try:
                scene["caption"] = image_captioner.caption_image(scene["frame_path"])
            except Exception as e:
                scene["caption"] = f"[Captioning failed: {e}]"

        # Enhance captions using LLM
        try:
            enhanced_scenes = caption_enhancer.enhance_scene_captions(scene_metadata["scenes"])
            scene_metadata["scenes"] = enhanced_scenes
        except Exception as e:
            print(f"Caption enhancement failed: {e}")
            # Continue without enhancement if it fails

        # Generate storyboard
        try:
            storyboard_path = storyboard_generator.generate_storyboard(
                scene_metadata["scenes"], 
                os.path.join(session_path, "storyboard.jpg")
            )
            scene_metadata["storyboard_path"] = storyboard_path
        except Exception as e:
            print(f"Storyboard generation failed: {e}")
            # Continue without storyboard if it fails

        # Re-save the metadata with the updated video path and transcript info
        scene_detector.save_metadata(scene_metadata, session_path)
        
        return {
            "message": "Video processed successfully",
            "session_path": session_path,
            "scene_metadata": scene_metadata,
            "status": "success"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Video processing endpoint for YouTube URL
@app.post("/process/youtube")
async def process_youtube_video(
    video_input: VideoInput,
    scene_request: SceneDetectionRequest = SceneDetectionRequest()
):
    try:
        if not video_input.youtube_url:
            raise HTTPException(status_code=400, detail="YouTube URL is required")

        # Validate YouTube URL
        if not youtube_handler.is_valid_youtube_url(video_input.youtube_url):
            raise HTTPException(status_code=400, detail="Invalid YouTube URL")

        # Download video to a temporary location
        temp_video_path = youtube_handler.download_video(video_input.youtube_url)
        
        # Process video for scene detection, which creates the session folder
        scene_metadata = scene_detector.process_video(
            video_path=temp_video_path,
            video_name=scene_request.video_name,
            use_pyscenedetect=scene_request.use_pyscenedetect
        )
        session_path = scene_metadata["session_path"]

        # Move the video file into its session folder
        final_video_filename = os.path.basename(temp_video_path)
        final_video_path = os.path.join(session_path, final_video_filename)
        shutil.move(temp_video_path, final_video_path)

        # Update metadata with the new, final path
        scene_metadata["video_path"] = final_video_path
        
        # Get scene transcripts using the final video path
        scene_timestamps = [(scene["start_time"], scene["end_time"]) for scene in scene_metadata["scenes"]]
        scene_transcripts = audio_transcriber.get_scene_transcripts(final_video_path, scene_timestamps)
        
        # Add transcripts to scene metadata
        for scene, transcript in zip(scene_metadata["scenes"], scene_transcripts):
            scene["transcript"] = transcript
            # Generate image caption for each scene frame
            try:
                scene["caption"] = image_captioner.caption_image(scene["frame_path"])
            except Exception as e:
                scene["caption"] = f"[Captioning failed: {e}]"

        # Enhance captions using LLM
        try:
            enhanced_scenes = caption_enhancer.enhance_scene_captions(scene_metadata["scenes"])
            scene_metadata["scenes"] = enhanced_scenes
        except Exception as e:
            print(f"Caption enhancement failed: {e}")
            # Continue without enhancement if it fails

        # Generate storyboard
        try:
            storyboard_path = storyboard_generator.generate_storyboard(
                scene_metadata["scenes"], 
                os.path.join(session_path, "storyboard.jpg")
            )
            scene_metadata["storyboard_path"] = storyboard_path
        except Exception as e:
            print(f"Storyboard generation failed: {e}")
            # Continue without storyboard if it fails

        # Re-save the metadata with the updated video path and transcript info
        scene_detector.save_metadata(scene_metadata, session_path)
        
        return {
            "message": "YouTube video processed successfully",
            "session_path": session_path,
            "scene_metadata": scene_metadata,
            "status": "success"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Get scene information endpoint
@app.get("/scenes/{session_id}")
async def get_scene_info(session_id: str):
    """Get information about scenes from a specific processing session"""
    try:
        # Look for the session folder
        session_path = os.path.join(SCENES_DIR, session_id)
        
        if not os.path.exists(session_path) or not os.path.isdir(session_path):
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Read metadata
        metadata_path = os.path.join(session_path, "metadata.json")
        if not os.path.exists(metadata_path):
            raise HTTPException(status_code=404, detail="Session metadata not found")
        
        import json
        with open(metadata_path, 'r') as f:
            metadata = json.load(f)
        
        return metadata
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Generate storyboard endpoint
@app.post("/generate-storyboard/{session_id}")
async def generate_storyboard(session_id: str):
    """Generate a storyboard for a specific session"""
    try:
        # Look for the session folder
        session_path = os.path.join(SCENES_DIR, session_id)
        
        if not os.path.exists(session_path) or not os.path.isdir(session_path):
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Generate storyboard
        storyboard_path = storyboard_generator.generate_storyboard_from_session(session_path)
        
        return {
            "message": "Storyboard generated successfully",
            "storyboard_path": storyboard_path,
            "status": "success"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Serve storyboard image endpoint
@app.get("/storyboard/{session_id}")
async def get_storyboard(session_id: str):
    """Serve the storyboard image for a specific session"""
    try:
        # Look for the session folder
        session_path = os.path.join(SCENES_DIR, session_id)
        
        if not os.path.exists(session_path) or not os.path.isdir(session_path):
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Look for storyboard file
        storyboard_path = os.path.join(session_path, "storyboard.jpg")
        if not os.path.exists(storyboard_path):
            raise HTTPException(status_code=404, detail="Storyboard not found")
        
        return FileResponse(storyboard_path, media_type="image/jpeg")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Serve individual scene frame endpoint
@app.get("/frame/{session_id}/{frame_filename}")
async def get_scene_frame(session_id: str, frame_filename: str):
    """Serve an individual scene frame image"""
    try:
        # Look for the session folder
        session_path = os.path.join(SCENES_DIR, session_id)
        
        if not os.path.exists(session_path) or not os.path.isdir(session_path):
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Look for frame file
        frame_path = os.path.join(session_path, "snippets", frame_filename)
        if not os.path.exists(frame_path):
            raise HTTPException(status_code=404, detail="Frame not found")
        
        return FileResponse(frame_path, media_type="image/jpeg")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# List all processing sessions
@app.get("/sessions")
async def list_sessions():
    """List all video processing sessions"""
    try:
        if not os.path.exists(SCENES_DIR):
            return {"sessions": []}
        
        sessions = []
        for folder in os.listdir(SCENES_DIR):
            folder_path = os.path.join(SCENES_DIR, folder)
            if os.path.isdir(folder_path):
                metadata_path = os.path.join(folder_path, "metadata.json")
                if os.path.exists(metadata_path):
                    import json
                    with open(metadata_path, 'r') as f:
                        metadata = json.load(f)
                    
                    # Check if storyboard exists
                    storyboard_exists = os.path.exists(os.path.join(folder_path, "storyboard.jpg"))
                    
                    sessions.append({
                        "session_id": folder,
                        "video_name": metadata.get("video_name", "Unknown"),
                        "total_scenes": metadata.get("total_scenes", 0),
                        "processing_timestamp": metadata.get("processing_timestamp", ""),
                        "session_path": folder_path,
                        "has_storyboard": storyboard_exists
                    })
        
        return {"sessions": sessions}
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
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True) 