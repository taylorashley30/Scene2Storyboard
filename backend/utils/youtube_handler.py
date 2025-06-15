import os
from typing import Optional
import uuid
import re
import yt_dlp

class YouTubeHandler:
    def __init__(self, download_dir: str = "uploads"):
        self.download_dir = download_dir
        os.makedirs(download_dir, exist_ok=True)

    def extract_video_id(self, url: str) -> Optional[str]:
        """Extract video ID from various YouTube URL formats"""
        patterns = [
            r'(?:v=|\/)([0-9A-Za-z_-]{11}).*',  # Standard and shortened URLs
            r'(?:embed\/)([0-9A-Za-z_-]{11})',   # Embed URLs
            r'(?:watch\?v=)([0-9A-Za-z_-]{11})'  # Watch URLs
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None

    def download_video(self, url: str) -> str:
        """Download a YouTube video and return its path"""
        try:
            # Extract video ID
            video_id = self.extract_video_id(url)
            if not video_id:
                raise Exception("Invalid YouTube URL format")

            # Generate unique filename
            unique_filename = f"{uuid.uuid4()}.mp4"
            file_path = os.path.join(self.download_dir, unique_filename)

            # Configure yt-dlp options
            ydl_opts = {
                'format': 'best[ext=mp4]',  # Best quality MP4
                'outtmpl': file_path,        # Output template
                'quiet': True,               # Suppress output
                'no_warnings': True,         # Suppress warnings
                'extract_flat': False,       # Don't extract playlist
            }

            # Download the video
            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([url])
                
                if not os.path.exists(file_path):
                    raise Exception("Download completed but file not found")
                return file_path
            except Exception as e:
                raise Exception(f"Failed to download video: {str(e)}")
            
        except Exception as e:
            raise Exception(f"Error downloading YouTube video: {str(e)}")

    def is_valid_youtube_url(self, url: str) -> bool:
        """Check if URL is a valid YouTube URL"""
        try:
            # Basic validation
            if not url:
                return False
                
            # Check if we can extract a video ID
            video_id = self.extract_video_id(url)
            if not video_id:
                return False
            
            # Try to get video info with yt-dlp
            with yt_dlp.YoutubeDL({'quiet': True, 'no_warnings': True}) as ydl:
                ydl.extract_info(url, download=False)
            return True
        except:
            return False 