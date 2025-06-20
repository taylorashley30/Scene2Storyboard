#!/usr/bin/env python3
"""
Debug script for scene detection
"""

import os
from utils.scene_detector import SceneDetector
from utils.frame_extractor import FrameExtractor

def debug_scene_detection():
    """Debug scene detection with different parameters"""
    
    video_path = "uploads/f7c09741-cf48-46c4-8c7d-d7e1892eacaa.mp4"
    
    if not os.path.exists(video_path):
        print(f"Video file not found: {video_path}")
        return
    
    print(f"Debugging scene detection for: {video_path}")
    
    # Initialize components
    scene_detector = SceneDetector()
    frame_extractor = FrameExtractor()
    
    # Get video info
    video_info = frame_extractor.get_video_info(video_path)
    print(f"Video Info: {video_info}")
    
    # Test OpenCV scene detection with different thresholds
    print("\nTesting OpenCV scene detection with different thresholds:")
    
    thresholds = [0.3, 0.5, 0.7, 0.9]
    for threshold in thresholds:
        try:
            scene_frames = scene_detector.detect_scenes_opencv(video_path, threshold=threshold)
            print(f"Threshold {threshold}: {len(scene_frames)} scene boundaries")
            if scene_frames:
                print(f"  Frame indices: {scene_frames}")
        except Exception as e:
            print(f"Threshold {threshold}: Error - {e}")
    
    # Test PySceneDetect
    print("\nTesting PySceneDetect:")
    try:
        scene_timestamps = scene_detector.detect_scenes_pyscenedetect(video_path)
        print(f"PySceneDetect: {len(scene_timestamps)} scenes")
        for i, (start, end) in enumerate(scene_timestamps):
            print(f"  Scene {i+1}: {start:.2f}s - {end:.2f}s")
    except Exception as e:
        print(f"PySceneDetect Error: {e}")
    
    # Force create at least one scene if none detected
    print("\nTesting forced scene creation:")
    try:
        # If no scenes detected, create one scene for the entire video
        if len(scene_timestamps) == 0:
            print("No scenes detected, creating one scene for entire video")
            duration = video_info['duration']
            scene_timestamps = [(0.0, duration)]
        
        # Extract frames
        session_path = scene_detector.create_session_folder("Debug Test")
        scenes_info = scene_detector.extract_scene_frames(video_path, scene_timestamps, session_path)
        
        print(f"Created {len(scenes_info)} scenes")
        for scene in scenes_info:
            print(f"  Scene {scene['scene_number']}: {scene['start_time']:.2f}s - {scene['end_time']:.2f}s")
            print(f"    Frame saved: {scene['frame_filename']}")
        
    except Exception as e:
        print(f"Error in forced scene creation: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_scene_detection() 