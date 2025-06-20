import cv2
import os
import numpy as np
from typing import List, Tuple, Dict
from PIL import Image, ImageEnhance

class FrameExtractor:
    def __init__(self):
        """Initialize FrameExtractor with image processing utilities"""
        pass
    
    def extract_frame_at_time(self, video_path: str, timestamp: float) -> np.ndarray:
        """
        Extract a single frame at a specific timestamp
        
        Args:
            video_path: Path to the video file
            timestamp: Time in seconds
            
        Returns:
            Frame as numpy array
        """
        cap = cv2.VideoCapture(video_path)
        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_number = int(timestamp * fps)
        
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
        ret, frame = cap.read()
        cap.release()
        
        if not ret:
            raise ValueError(f"Could not extract frame at timestamp {timestamp}")
        
        return frame
    
    def extract_frames_at_intervals(self, video_path: str, interval: float = 1.0) -> List[Tuple[float, np.ndarray]]:
        """
        Extract frames at regular intervals
        
        Args:
            video_path: Path to the video file
            interval: Time interval between frames in seconds
            
        Returns:
            List of (timestamp, frame) tuples
        """
        cap = cv2.VideoCapture(video_path)
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration = total_frames / fps
        
        frames = []
        current_time = 0.0
        
        while current_time < duration:
            frame_number = int(current_time * fps)
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
            ret, frame = cap.read()
            
            if ret:
                frames.append((current_time, frame))
            
            current_time += interval
        
        cap.release()
        return frames
    
    def enhance_frame(self, frame: np.ndarray, brightness: float = 1.0, 
                     contrast: float = 1.0, saturation: float = 1.0) -> np.ndarray:
        """
        Enhance frame quality using PIL
        
        Args:
            frame: Input frame as numpy array
            brightness: Brightness factor (0.0 to 2.0)
            contrast: Contrast factor (0.0 to 2.0)
            saturation: Saturation factor (0.0 to 2.0)
            
        Returns:
            Enhanced frame as numpy array
        """
        # Convert BGR to RGB
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # Convert to PIL Image
        pil_image = Image.fromarray(frame_rgb)
        
        # Apply enhancements
        if brightness != 1.0:
            enhancer = ImageEnhance.Brightness(pil_image)
            pil_image = enhancer.enhance(brightness)
        
        if contrast != 1.0:
            enhancer = ImageEnhance.Contrast(pil_image)
            pil_image = enhancer.enhance(contrast)
        
        if saturation != 1.0:
            enhancer = ImageEnhance.Color(pil_image)
            pil_image = enhancer.enhance(saturation)
        
        # Convert back to numpy array and BGR
        enhanced_rgb = np.array(pil_image)
        enhanced_bgr = cv2.cvtColor(enhanced_rgb, cv2.COLOR_RGB2BGR)
        
        return enhanced_bgr
    
    def resize_frame(self, frame: np.ndarray, width: int = None, height: int = None, 
                    maintain_aspect: bool = True) -> np.ndarray:
        """
        Resize frame to specified dimensions
        
        Args:
            frame: Input frame
            width: Target width
            height: Target height
            maintain_aspect: Whether to maintain aspect ratio
            
        Returns:
            Resized frame
        """
        if width is None and height is None:
            return frame
        
        h, w = frame.shape[:2]
        
        if maintain_aspect:
            if width is None:
                # Calculate width based on height
                aspect_ratio = w / h
                width = int(height * aspect_ratio)
            elif height is None:
                # Calculate height based on width
                aspect_ratio = h / w
                height = int(width * aspect_ratio)
        
        return cv2.resize(frame, (width, height))
    
    def get_video_info(self, video_path: str) -> Dict:
        """
        Get video information
        
        Args:
            video_path: Path to the video file
            
        Returns:
            Dictionary with video information
        """
        cap = cv2.VideoCapture(video_path)
        
        info = {
            "fps": cap.get(cv2.CAP_PROP_FPS),
            "frame_count": int(cap.get(cv2.CAP_PROP_FRAME_COUNT)),
            "width": int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
            "height": int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
            "duration": cap.get(cv2.CAP_PROP_FRAME_COUNT) / cap.get(cv2.CAP_PROP_FPS),
            "codec": int(cap.get(cv2.CAP_PROP_FOURCC))
        }
        
        cap.release()
        return info
    
    def save_frame(self, frame: np.ndarray, output_path: str, quality: int = 95) -> bool:
        """
        Save frame to file
        
        Args:
            frame: Frame to save
            output_path: Output file path
            quality: JPEG quality (1-100)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # Save with specified quality
            cv2.imwrite(output_path, frame, [cv2.IMWRITE_JPEG_QUALITY, quality])
            return True
        except Exception as e:
            print(f"Error saving frame: {e}")
            return False 