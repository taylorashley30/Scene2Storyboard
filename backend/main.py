#!/usr/bin/env python3
"""
Scene2Storyboard Backend API
Main FastAPI application for video processing and storyboard generation
"""

import os
import time
from pathlib import Path

# Load .env from backend directory so GEMINI_API_KEY, S2S_WHISPER_MODEL_SIZE, etc. are set
_env_path = Path(__file__).resolve().parent / ".env"
if _env_path.exists():
    from dotenv import load_dotenv
    load_dotenv(_env_path)

import re
import shutil
from typing import Optional
import cv2
from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi import Query
from pydantic import BaseModel

# Import utility modules
from utils.file_handler import FileHandler
from utils.youtube_handler import YouTubeHandler
from utils.scene_detector import SceneDetector
from utils.audio_transcriber import AudioTranscriber
from utils.image_captioner import ImageCaptioner
from utils.caption_enhancer import CaptionEnhancer
from utils.panel_expander import expand_scenes_to_panels, assign_distinct_frames_to_panels, deduplicate_panel_captions
from utils.storyboard_generator import StoryboardGenerator

# Base paths (independent of where the server is started from)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SCENES_DIR = os.path.join(BASE_DIR, "scenes")
os.makedirs(SCENES_DIR, exist_ok=True)


def get_video_duration_seconds(video_path: str) -> Optional[float]:
    """Return video duration in seconds using OpenCV, or None if unavailable."""
    if not video_path or not os.path.exists(video_path):
        print(f"[Main] Video path not found for duration: {video_path}")
        return None

    cap = cv2.VideoCapture(video_path)
    try:
        fps = cap.get(cv2.CAP_PROP_FPS) or 0.0
        frame_count = cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0.0
    finally:
        cap.release()

    if fps <= 0 or frame_count <= 0:
        print(f"[Main] Could not determine FPS/frame count for: {video_path}")
        return None

    return float(frame_count / fps)

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
scene_detector = SceneDetector(scenes_dir=SCENES_DIR)
audio_transcriber = AudioTranscriber()
image_captioner = ImageCaptioner()
caption_enhancer = CaptionEnhancer()
storyboard_generator = StoryboardGenerator()

# Pydantic models
class VideoInput(BaseModel):
    youtube_url: Optional[str] = None

class ProcessYoutubeRequest(BaseModel):
    """Single body for /process/youtube - flat structure for simpler frontend requests."""
    youtube_url: Optional[str] = None
    use_pyscenedetect: bool = True
    video_name: Optional[str] = None

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
    start_time = time.time()
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

        # Compute and store video duration (seconds) for tracking
        video_duration_seconds = get_video_duration_seconds(final_video_path)
        if video_duration_seconds is not None:
            scene_metadata["video_duration_seconds"] = video_duration_seconds
        
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

        # Enhance captions (optional LLM when GEMINI_API_KEY is set, else rule-based)
        video_context = {"video_name": scene_metadata.get("video_name", "")}
        try:
            enhanced_scenes = caption_enhancer.enhance_scene_captions(
                scene_metadata["scenes"], video_context=video_context
            )
            scene_metadata["scenes"] = enhanced_scenes
        except Exception as e:
            print(f"Caption enhancement failed: {e}")
            # Continue without enhancement if it fails

        # Expand long captions into additional panels
        panels_data = expand_scenes_to_panels(scene_metadata["scenes"], max_caption_chars=180)
        # Deduplicate captions: avoid repeating whole sentences across panels
        panels_data = deduplicate_panel_captions(panels_data)
        # When panels share a scene, extract distinct frames at evenly spaced timestamps
        panels_data = assign_distinct_frames_to_panels(
            panels_data, final_video_path, session_path
        )

        # Generate storyboard (multi-page for long videos)
        try:
            storyboard_path = storyboard_generator.generate_storyboard(
                panels_data,
                os.path.join(session_path, "storyboard.jpg"),
                story_arc_summary=scene_metadata.get("video_name"),
            )
            scene_metadata["storyboard_path"] = storyboard_path
            scene_metadata["storyboard_pdf_path"] = getattr(
                storyboard_generator, "_last_pdf_path", None
            )
            scene_metadata["storyboard_page_paths"] = getattr(
                storyboard_generator, "_last_page_paths", [storyboard_path]
            )
        except Exception as e:
            print(f"Storyboard generation failed: {e}")
            # Continue without storyboard if it fails

        # Store panels and summary for frontend (multiple snippets per scene)
        scene_metadata["panels"] = panels_data
        scene_metadata["story_arc_summary"] = scene_metadata.get("video_name", "")

        # Re-save the metadata with the updated video path and transcript info
        # and include timing metrics.
        processing_time_seconds = time.time() - start_time
        scene_metadata["processing_time_seconds"] = processing_time_seconds
        scene_detector.save_metadata(scene_metadata, session_path)
        
        return {
            "message": "Video processed successfully",
            "session_path": session_path,
            "scene_metadata": scene_metadata,
            "processing_time_seconds": processing_time_seconds,
            "video_duration_seconds": scene_metadata.get("video_duration_seconds"),
            "status": "success"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Video processing endpoint for YouTube URL
@app.post("/process/youtube")
async def process_youtube_video(req: ProcessYoutubeRequest):
    start_time = time.time()
    try:
        if not req.youtube_url:
            raise HTTPException(status_code=400, detail="Video URL is required (YouTube or Instagram)")

        # Validate video URL (YouTube or Instagram)
        if not youtube_handler.is_valid_video_url(req.youtube_url):
            raise HTTPException(status_code=400, detail="Invalid video URL. Supported: YouTube (watch, shorts, youtu.be) or Instagram (posts, reels)")

        # Get video title and optional description for nicer UX and narrative context
        video_name = req.video_name
        video_description = None
        if not video_name:
            try:
                info = youtube_handler.get_video_info(req.youtube_url)
                video_name = (info.get("title") or "Video").strip()[:80]  # Sanitize and truncate
                video_description = (info.get("description") or "").strip()[:200]
            except Exception:
                video_name = None

        # Download video to a temporary location
        print("[Pipeline] Downloading video...")
        temp_video_path = youtube_handler.download_video(req.youtube_url)
        print("[Pipeline] Download done. Detecting scenes...")

        # Process video for scene detection, which creates the session folder
        scene_metadata = scene_detector.process_video(
            video_path=temp_video_path,
            video_name=video_name,
            use_pyscenedetect=req.use_pyscenedetect
        )
        session_path = scene_metadata["session_path"]

        # Move the video file into its session folder
        final_video_filename = os.path.basename(temp_video_path)
        final_video_path = os.path.join(session_path, final_video_filename)
        shutil.move(temp_video_path, final_video_path)

        # Update metadata with the new, final path
        scene_metadata["video_path"] = final_video_path

        # Compute and store video duration (seconds) for tracking
        video_duration_seconds = get_video_duration_seconds(final_video_path)
        if video_duration_seconds is not None:
            scene_metadata["video_duration_seconds"] = video_duration_seconds

        # Get scene transcripts using the final video path
        print("[Pipeline] Transcribing audio (Whisper — this can take 1–2+ min)...")
        scene_timestamps = [(scene["start_time"], scene["end_time"]) for scene in scene_metadata["scenes"]]
        scene_transcripts = audio_transcriber.get_scene_transcripts(final_video_path, scene_timestamps)
        print("[Pipeline] Transcription done. Captioning images (BLIP)...")

        # Add transcripts to scene metadata
        for scene, transcript in zip(scene_metadata["scenes"], scene_transcripts):
            scene["transcript"] = transcript
            # Generate image caption for each scene frame
            try:
                scene["caption"] = image_captioner.caption_image(scene["frame_path"])
            except Exception as e:
                scene["caption"] = f"[Captioning failed: {e}]"

        # Enhance captions (Gemini when GEMINI_API_KEY is set, else rule-based)
        video_context = {"video_name": scene_metadata.get("video_name", "")}
        if video_description:
            video_context["description"] = video_description
        print("[Pipeline] Enhancing captions (Gemini or rule-based)...")
        try:
            enhanced_scenes = caption_enhancer.enhance_scene_captions(
                scene_metadata["scenes"], video_context=video_context
            )
            scene_metadata["scenes"] = enhanced_scenes
        except Exception as e:
            print(f"Caption enhancement failed: {e}")
            # Continue without enhancement if it fails

        # Expand long captions into additional panels
        panels_data = expand_scenes_to_panels(scene_metadata["scenes"], max_caption_chars=180)
        # Deduplicate captions: avoid repeating whole sentences across panels
        panels_data = deduplicate_panel_captions(panels_data)
        # When panels share a scene, extract distinct frames at evenly spaced timestamps
        panels_data = assign_distinct_frames_to_panels(
            panels_data, final_video_path, session_path
        )

        # Generate storyboard
        print("[Pipeline] Generating storyboard image...")
        try:
            storyboard_path = storyboard_generator.generate_storyboard(
                panels_data,
                os.path.join(session_path, "storyboard.jpg"),
                story_arc_summary=scene_metadata.get("video_name"),
            )
            scene_metadata["storyboard_path"] = storyboard_path
            scene_metadata["storyboard_pdf_path"] = getattr(
                storyboard_generator, "_last_pdf_path", None
            )
            scene_metadata["storyboard_page_paths"] = getattr(
                storyboard_generator, "_last_page_paths", [storyboard_path]
            )
        except Exception as e:
            print(f"Storyboard generation failed: {e}")
            # Continue without storyboard if it fails

        # Store panels and summary for frontend (multiple snippets per scene)
        scene_metadata["panels"] = panels_data
        scene_metadata["story_arc_summary"] = scene_metadata.get("video_name", "")

        # Re-save the metadata with the updated video path and transcript info
        # and include timing metrics.
        processing_time_seconds = time.time() - start_time
        scene_metadata["processing_time_seconds"] = processing_time_seconds
        scene_detector.save_metadata(scene_metadata, session_path)
        print(f"[Pipeline] Done. Total processing time: {processing_time_seconds:.2f} seconds.")

        return {
            "message": "Video processed successfully",
            "session_path": session_path,
            "scene_metadata": scene_metadata,
            "processing_time_seconds": processing_time_seconds,
            "video_duration_seconds": scene_metadata.get("video_duration_seconds"),
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

        # Augment with storyboard page paths if missing (e.g. after regenerate or legacy sessions)
        if "storyboard_page_paths" not in metadata or not metadata.get("storyboard_page_paths"):
            page_paths = []
            for n in range(1, 100):
                p = os.path.join(session_path, f"storyboard_page_{n}.jpg")
                if os.path.exists(p):
                    page_paths.append(p)
                elif n > 1:
                    break
            if page_paths:
                metadata["storyboard_page_paths"] = page_paths

        return metadata
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Generate storyboard endpoint
@app.post("/generate-storyboard/{session_id}")
async def generate_storyboard(session_id: str):
    """Generate a storyboard for a specific session"""
    try:
        session_path = os.path.join(SCENES_DIR, session_id)
        if not os.path.exists(session_path) or not os.path.isdir(session_path):
            raise HTTPException(status_code=404, detail="Session not found")

        storyboard_path = storyboard_generator.generate_storyboard_from_session(session_path)

        # Update metadata with new storyboard paths
        metadata_path = os.path.join(session_path, "metadata.json")
        if os.path.exists(metadata_path):
            import json
            with open(metadata_path, 'r') as f:
                metadata = json.load(f)
            metadata["storyboard_path"] = storyboard_path
            metadata["storyboard_pdf_path"] = getattr(storyboard_generator, "_last_pdf_path", None)
            metadata["storyboard_page_paths"] = getattr(storyboard_generator, "_last_page_paths", [storyboard_path])
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f, indent=2)

        return {
            "message": "Storyboard generated successfully",
            "storyboard_path": storyboard_path,
            "status": "success"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Serve storyboard image endpoint
@app.get("/storyboard/{session_id}")
async def get_storyboard(
    session_id: str,
    page: Optional[int] = Query(None, description="Page number (1-based). Omit for page 1.")
):
    """Serve the storyboard image (page 1 by default, or specified page when multi-page)."""
    try:
        session_path = os.path.join(SCENES_DIR, session_id)
        if not os.path.exists(session_path) or not os.path.isdir(session_path):
            raise HTTPException(status_code=404, detail="Session not found")

        if page is not None and page >= 1:
            page_path = os.path.join(session_path, f"storyboard_page_{page}.jpg")
            if os.path.exists(page_path):
                return FileResponse(page_path, media_type="image/jpeg")

        storyboard_path = os.path.join(session_path, "storyboard.jpg")
        if not os.path.exists(storyboard_path):
            raise HTTPException(status_code=404, detail="Storyboard not found")

        return FileResponse(storyboard_path, media_type="image/jpeg")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Export storyboard as PNG, JPEG, or PDF
@app.get("/storyboard/{session_id}/export")
async def export_storyboard(
    session_id: str,
    format: str = Query("png", description="Export format: png, jpeg, or pdf")
):
    """Export the storyboard as PNG, JPEG, or PDF. PDF uses multi-page when available."""
    try:
        session_path = os.path.join(SCENES_DIR, session_id)
        if not os.path.exists(session_path) or not os.path.isdir(session_path):
            raise HTTPException(status_code=404, detail="Session not found")

        storyboard_jpg = os.path.join(session_path, "storyboard.jpg")
        storyboard_pdf = os.path.join(session_path, "storyboard.pdf")
        if not os.path.exists(storyboard_jpg):
            raise HTTPException(status_code=404, detail="Storyboard not found")

        fmt = format.lower().strip()
        if fmt == "jpg":
            fmt = "jpeg"

        if fmt == "jpeg" or fmt == "png":
            # Collect all storyboard page images
            image_paths = []
            for n in range(1, 100):
                p = os.path.join(session_path, f"storyboard_page_{n}.jpg")
                if os.path.exists(p):
                    image_paths.append(p)
                elif n > 1:
                    break
            if not image_paths:
                image_paths = [storyboard_jpg]

            import zipfile
            import io
            from PIL import Image

            buf = io.BytesIO()
            with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
                for i, path in enumerate(image_paths):
                    img = Image.open(path)
                    if img.mode in ("RGBA", "P"):
                        img = img.convert("RGB")
                    img_buf = io.BytesIO()
                    img.save(img_buf, "PNG" if fmt == "png" else "JPEG", quality=95)
                    img_buf.seek(0)
                    ext = "png" if fmt == "png" else "jpg"
                    arcname = f"storyboard_page_{i + 1}.{ext}" if len(image_paths) > 1 else f"storyboard.{ext}"
                    zf.writestr(arcname, img_buf.getvalue())

            buf.seek(0)
            vid_name = "storyboard"
            try:
                import json
                with open(os.path.join(session_path, "metadata.json")) as f:
                    vid_name = json.load(f).get("video_name", "storyboard") or "storyboard"
            except Exception:
                pass
            safe_name = re.sub(r'[^\w\-]', '_', str(vid_name))[:80]
            filename = f"{safe_name}_storyboard_pages.zip"
            from fastapi.responses import Response
            return Response(
                content=buf.getvalue(),
                media_type="application/zip",
                headers={"Content-Disposition": f'attachment; filename="{filename}"'}
            )

        if fmt == "pdf":
            vid_name = "storyboard"
            try:
                import json
                with open(os.path.join(session_path, "metadata.json")) as f:
                    vid_name = json.load(f).get("video_name", "storyboard") or "storyboard"
            except Exception:
                pass
            safe_name = re.sub(r'[^\w\-]', '_', str(vid_name))[:80]
            filename = f"{safe_name}_storyboard.pdf"
            # Prefer multi-page PDF when available (longer videos)
            if os.path.exists(storyboard_pdf):
                return FileResponse(
                    storyboard_pdf,
                    media_type="application/pdf",
                    filename=filename,
                    headers={"Content-Disposition": f'attachment; filename="{filename}"'}
                )
            import img2pdf
            with open(storyboard_jpg, "rb") as f:
                pdf_bytes = img2pdf.convert(f)
            from fastapi.responses import Response
            return Response(
                content=pdf_bytes,
                media_type="application/pdf",
                headers={"Content-Disposition": f'attachment; filename="{filename}"'}
            )

        raise HTTPException(status_code=400, detail="Invalid format. Use png, jpeg, or pdf")
    except HTTPException:
        raise
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

# Delete a session (storyboard and all associated files)
@app.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    """Delete a processing session and its storyboard"""
    try:
        session_path = os.path.join(SCENES_DIR, session_id)
        if not os.path.exists(session_path) or not os.path.isdir(session_path):
            raise HTTPException(status_code=404, detail="Session not found")
        shutil.rmtree(session_path)
        return {"message": "Session deleted", "status": "success"}
    except HTTPException:
        raise
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
                    panels = metadata.get("panels") or []
                    total_scenes = metadata.get("total_scenes", 0)
                    total_panels = len(panels) if panels else total_scenes
                    
                    sessions.append({
                        "session_id": folder,
                        "video_name": metadata.get("video_name", "Unknown"),
                        "total_scenes": total_scenes,
                        "total_panels": total_panels,
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