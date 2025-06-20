import yt_dlp
import os
from typing import Optional
import uuid
from yt_dlp import YoutubeDL

class YouTubeHandler:
    def __init__(self, download_dir: str = "uploads"):
        self.download_dir = download_dir
        os.makedirs(self.download_dir, exist_ok=True)

    def download_video(self, url: str) -> str:
        """Download a video from YouTube and return the file path."""
        unique_id = str(uuid.uuid4())
        output_template = os.path.join(self.download_dir, f"{unique_id}.%(ext)s")

        ydl_opts = {
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
            'outtmpl': output_template,
            'merge_output_format': 'mp4',
        }

        with YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(url, download=True)
            # The actual filename is determined by yt-dlp, including the extension
            filename = ydl.prepare_filename(info_dict)
            return filename

    def is_valid_youtube_url(self, url: str) -> bool:
        """Check if the URL is a valid YouTube URL."""
        return "youtube.com/watch?v=" in url or "youtu.be/" in url
    
    def get_video_info(self, url: str) -> dict:
        """Get video information without downloading"""
        try:
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'extract_flat': True,
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                
                return {
                    'title': info.get('title', 'Unknown'),
                    'duration': info.get('duration', 0),
                    'uploader': info.get('uploader', 'Unknown'),
                    'view_count': info.get('view_count', 0),
                    'upload_date': info.get('upload_date', 'Unknown'),
                    'description': info.get('description', '')[:200] + '...' if info.get('description') else ''
                }
        except Exception as e:
            raise Exception(f"Error getting video info: {str(e)}") 