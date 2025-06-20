import os
import whisper
from moviepy import VideoFileClip
from typing import Dict, List, Optional, Tuple

class AudioTranscriber:
    def __init__(self, model_size: str = "base"):
        """
        Initialize the AudioTranscriber with a Whisper model.
        
        Args:
            model_size (str): Size of the Whisper model to use. Options: "tiny", "base", "small", "medium", "large"
        """
        self.model = whisper.load_model(model_size)
    
    def extract_audio(self, video_path: str, output_path: Optional[str] = None) -> str:
        """
        Extract audio from a video file.
        
        Args:
            video_path (str): Path to the input video file
            output_path (str, optional): Path to save the audio file. If None, uses video_path with .wav extension
            
        Returns:
            str: Path to the extracted audio file
        """
        if output_path is None:
            output_path = os.path.splitext(video_path)[0] + ".wav"
            
        video = VideoFileClip(video_path)
        video.audio.write_audiofile(
            output_path,
            fps=16000,
            ffmpeg_params=["-ac", "1"]  # Convert to mono
        )
        video.close()
        return output_path
    
    def transcribe_audio(self, audio_path: str) -> Dict:
        """
        Transcribe audio using Whisper.
        
        Args:
            audio_path (str): Path to the audio file
            
        Returns:
            Dict: Transcription result containing text and segments
        """
        result = self.model.transcribe(audio_path)
        return result
    
    def get_scene_transcripts(self, video_path: str, scene_timestamps: List[Tuple[float, float]]) -> List[str]:
        """
        Get transcripts for specific scenes in a video.
        
        Args:
            video_path (str): Path to the video file
            scene_timestamps (List[Tuple[float, float]]): List of (start_time, end_time) tuples for each scene
            
        Returns:
            List[str]: List of transcripts for each scene
        """
        # Extract audio if it doesn't exist
        audio_path = os.path.splitext(video_path)[0] + ".wav"
        if not os.path.exists(audio_path):
            audio_path = self.extract_audio(video_path)
        
        # Get full transcription
        result = self.transcribe_audio(audio_path)
        
        # Map segments to scenes
        scene_transcripts = []
        for start_time, end_time in scene_timestamps:
            scene_text = []
            for segment in result["segments"]:
                seg_start = segment["start"]
                seg_end = segment["end"]
                
                # If segment overlaps with scene
                if (seg_start <= end_time and seg_end >= start_time):
                    scene_text.append(segment["text"])
            
            scene_transcripts.append(" ".join(scene_text))
        
        return scene_transcripts 