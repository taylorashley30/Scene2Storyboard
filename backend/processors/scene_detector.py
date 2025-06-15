import cv2
import numpy as np
from scenedetect import detect, ContentDetector, SceneManager, open_video
from scenedetect.video_splitter import split_video_ffmpeg
from typing import List, Tuple, Optional
import os
from pathlib import Path

class SceneDetector:
    def __init__(self, output_dir: str = "uploads/scenes"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    def detect_scenes(self, video_path: str, threshold: float = 30.0) -> List[Tuple[float, float]]:
        """
        Detect scenes in a video using PySceneDetect.
        Returns a list of tuples containing (start_time, end_time) for each scene.
        """
        try:
            # Create a scene manager and add ContentDetector
            scene_manager = SceneManager()
            scene_manager.add_detector(ContentDetector(threshold=threshold))

            # Open the video
            video = open_video(video_path)
            
            # Detect scenes
            scene_manager.detect_scenes(video)
            
            # Get the scene list
            scene_list = scene_manager.get_scene_list()
            
            # Convert to list of (start_time, end_time) tuples
            scenes = [(scene[0].get_seconds(), scene[1].get_seconds()) 
                     for scene in scene_list]
            
            return scenes
        except Exception as e:
            raise Exception(f"Error detecting scenes: {str(e)}")

    def extract_scene_frames(self, video_path: str, scenes: List[Tuple[float, float]], 
                           num_frames: int = 1) -> List[str]:
        """
        Extract representative frames from each scene.
        Returns a list of paths to the extracted frames.
        """
        try:
            # Open the video
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                raise Exception("Could not open video file")

            frame_paths = []
            
            for i, (start_time, end_time) in enumerate(scenes):
                # Calculate the middle of the scene
                middle_time = (start_time + end_time) / 2
                
                # Set the video position to the middle of the scene
                cap.set(cv2.CAP_PROP_POS_MSEC, middle_time * 1000)
                
                # Read the frame
                ret, frame = cap.read()
                if not ret:
                    continue
                
                # Save the frame
                frame_path = os.path.join(self.output_dir, f"scene_{i:03d}.jpg")
                cv2.imwrite(frame_path, frame)
                frame_paths.append(frame_path)

            cap.release()
            return frame_paths
        except Exception as e:
            raise Exception(f"Error extracting scene frames: {str(e)}")

    def process_video(self, video_path: str, threshold: float = 30.0, 
                     num_frames: int = 1) -> Tuple[List[Tuple[float, float]], List[str]]:
        """
        Process a video to detect scenes and extract frames.
        Returns a tuple of (scenes, frame_paths).
        """
        try:
            # Detect scenes
            scenes = self.detect_scenes(video_path, threshold)
            
            # Extract frames
            frame_paths = self.extract_scene_frames(video_path, scenes, num_frames)
            
            return scenes, frame_paths
        except Exception as e:
            raise Exception(f"Error processing video: {str(e)}")

    def cleanup(self):
        """Clean up extracted frames"""
        try:
            for file in Path(self.output_dir).glob("*.jpg"):
                file.unlink()
        except Exception as e:
            raise Exception(f"Error cleaning up frames: {str(e)}") 