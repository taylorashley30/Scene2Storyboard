import cv2
import os
import uuid
from datetime import datetime
from typing import List, Tuple, Dict
import numpy as np
from scenedetect import detect, ContentDetector, SceneManager, VideoManager
from scenedetect.video_manager import VideoManager
from scenedetect.stats_manager import StatsManager
from scenedetect.detectors import ContentDetector
from scenedetect.scene_manager import save_images
import json

class SceneDetector:
    def __init__(self, scenes_dir="scenes"):
        self.scenes_dir = scenes_dir
        os.makedirs(self.scenes_dir, exist_ok=True)
    
    def _create_session_folder(self, video_name: str) -> str:
        """Create a unique folder for the processing session."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        # Sanitize video name and create a unique session ID
        safe_name = "".join(c for c in video_name if c.isalnum() or c in (' ', '-', '_')).rstrip().replace(' ', '_')[:20]
        session_id = f"{timestamp}_{safe_name}_{os.urandom(4).hex()}"
        session_path = os.path.join(self.scenes_dir, session_id)
        os.makedirs(session_path, exist_ok=True)
        return session_path
    
    def save_metadata(self, metadata: dict, session_path: str):
        """Saves the metadata dictionary to a JSON file."""
        metadata_path = os.path.join(session_path, "metadata.json")
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=4)
    
    def detect_scenes_opencv(self, video_path: str, threshold: float = 0.5) -> List[int]:
        """
        Detect scenes using OpenCV histogram comparison
        
        Args:
            video_path: Path to the video file
            threshold: Threshold for scene change detection (0.0 to 1.0)
            
        Returns:
            List of frame indices where scenes change
        """
        cap = cv2.VideoCapture(video_path)
        scene_frames = []
        prev_hist = None
        frame_index = 0
        
        # Add first frame as scene start
        scene_frames.append(0)
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            # Compute color histogram for this frame
            hist = cv2.calcHist([frame], channels=[0, 1, 2], mask=None, 
                               histSize=[16, 16, 16], ranges=[0, 256] * 3)
            cv2.normalize(hist, hist, 0, 1, cv2.NORM_MINMAX)
            
            if prev_hist is not None:
                # Compare histograms
                diff = cv2.compareHist(prev_hist, hist, cv2.HISTCMP_CORREL)
                
                # Low correlation indicates scene change
                if diff < threshold:
                    scene_frames.append(frame_index)
            
            prev_hist = hist
            frame_index += 1
        
        cap.release()
        return scene_frames
    
    def _detect_scenes_pyscenedetect(self, video_path: str, session_path: str) -> List[Dict]:
        """Detects scenes using PySceneDetect and saves a representative frame for each."""
        try:
            video_manager = VideoManager([video_path])
            scene_manager = SceneManager()
            scene_manager.add_detector(ContentDetector())
            video_manager.set_downscale_factor()
            video_manager.start()
            scene_manager.detect_scenes(frame_source=video_manager)
            scene_list_raw = scene_manager.get_scene_list()

            # Each scene is a tuple of (start_timecode, end_timecode)
            if not scene_list_raw:
                 # If no scenes are detected, treat the whole video as one scene
                cap = cv2.VideoCapture(video_path)
                fps = cap.get(cv2.CAP_PROP_FPS)
                frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                duration = frame_count / fps
                cap.release()
                from scenedetect import FrameTimecode
                scene_list_raw = [(FrameTimecode(0, fps), FrameTimecode(frame_count, fps))]

            # Save middle frame for each scene
            images_path = os.path.join(session_path)
            save_images(
                scene_list=scene_list_raw,
                video=video_manager,
                num_images=1,
                output_dir=images_path,
                image_name_template='scene_$SCENE_NUMBER'
            )

            scene_data = []
            for i, scene in enumerate(scene_list_raw):
                start_time = scene[0].get_seconds()
                end_time = scene[1].get_seconds()
                frame_filename = f"scene_{i+1:03d}.jpg"
                frame_path = os.path.join(images_path, frame_filename)
                
                # PySceneDetect might save with a different number format
                # e.g. scene_001.jpg vs scene_1.jpg. Check for existence
                if not os.path.exists(frame_path):
                    # Try alternate name format from save_images
                    alt_frame_filename = f"scene_{i+1}.jpg"
                    alt_frame_path = os.path.join(images_path, alt_frame_filename)
                    if os.path.exists(alt_frame_path):
                        frame_path = alt_frame_path
                        frame_filename = alt_frame_filename
                    else:
                        # As a fallback, skip if image not found
                        continue
                
                scene_data.append({
                    "scene_number": i + 1,
                    "start_time": start_time,
                    "end_time": end_time,
                    "duration": end_time - start_time,
                    "frame_path": frame_path,
                    "frame_filename": frame_filename
                })
            
            video_manager.release()
            return scene_data

        except Exception as e:
            print(f"Error during PySceneDetect processing: {e}")
            return []
    
    def _convert_frames_to_timestamps(self, video_path: str, frame_indices: List[int]) -> List[Tuple[float, float]]:
        """
        Convert frame indices to timestamps
        
        Args:
            video_path: Path to the video file
            frame_indices: List of frame indices
            
        Returns:
            List of (start_time, end_time) tuples
        """
        cap = cv2.VideoCapture(video_path)
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        cap.release()
        
        timestamps = []
        for i in range(len(frame_indices)):
            start_frame = frame_indices[i]
            start_time = start_frame / fps
            
            if i + 1 < len(frame_indices):
                end_frame = frame_indices[i + 1] - 1
            else:
                end_frame = total_frames - 1
            
            end_time = end_frame / fps
            timestamps.append((start_time, end_time))
        
        return timestamps
    
    def process_video(self, video_path: str, video_name: str, use_pyscenedetect: bool = True):
        """
        Processes a video to detect scenes and extract representative frames.
        """
        if not video_name:
            video_name = os.path.splitext(os.path.basename(video_path))[0]

        session_path = self._create_session_folder(video_name)
        
        # We are simplifying to only use PySceneDetect as it's more robust
        scenes = self._detect_scenes_pyscenedetect(video_path, session_path)
        
        metadata = {
            "video_path": video_path, # This will be updated in main.py after move
            "video_name": video_name,
            "session_path": session_path,
            "total_scenes": len(scenes),
            "scenes": scenes,
            "processing_timestamp": datetime.now().isoformat()
        }
        
        self.save_metadata(metadata, session_path)
        
        return metadata