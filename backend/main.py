from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
import os
import shutil
from typing import Optional
from pydantic import BaseModel
from utils.file_handler import FileHandler
from utils.youtube_handler import YouTubeHandler
from utils.scene_detector import SceneDetector
from utils.audio_transcriber import AudioTranscriber
from utils.image_captioner import ImageCaptioner
from utils.caption_enhancer import CaptionEnhancer

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

# Define and create base directories
UPLOADS_DIR = "uploads"
SCENES_DIR = "scenes"
os.makedirs(UPLOADS_DIR, exist_ok=True)
os.makedirs(SCENES_DIR, exist_ok=True)

# Initialize handlers
file_handler = FileHandler(upload_dir=UPLOADS_DIR)
youtube_handler = YouTubeHandler(download_dir=UPLOADS_DIR)
scene_detector = SceneDetector(scenes_dir=SCENES_DIR)
audio_transcriber = AudioTranscriber(model_size="medium")  # Using medium model for better accuracy
image_captioner = ImageCaptioner()
caption_enhancer = CaptionEnhancer()  # LLM caption enhancement

# Models
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
                    
                    sessions.append({
                        "session_id": folder,
                        "video_name": metadata.get("video_name", "Unknown"),
                        "total_scenes": metadata.get("total_scenes", 0),
                        "processing_timestamp": metadata.get("processing_timestamp", ""),
                        "session_path": folder_path
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
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True) 