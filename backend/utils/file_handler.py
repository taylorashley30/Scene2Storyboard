import os
import shutil
from typing import Optional
from fastapi import UploadFile
import uuid

class FileHandler:
    def __init__(self, upload_dir: str = "uploads"):
        self.upload_dir = upload_dir
        os.makedirs(self.upload_dir, exist_ok=True)

    async def save_upload_file(self, file: UploadFile) -> str:
        """Saves an uploaded file to the upload directory with a unique name."""
        _, extension = os.path.splitext(file.filename)
        unique_filename = f"{uuid.uuid4()}{extension}"
        file_path = os.path.join(self.upload_dir, unique_filename)
        
        with open(file_path, "wb") as buffer:
            buffer.write(await file.read())
            
        return file_path

    def cleanup_file(self, file_path: str) -> None:
        """Delete a file if it exists"""
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
        except Exception as e:
            raise Exception(f"Error cleaning up file: {str(e)}")

    def get_file_extension(self, filename: str) -> str:
        """Get file extension from filename"""
        return os.path.splitext(filename)[1].lower()

    def is_valid_video_file(self, filename: str) -> bool:
        """Check if the file has a valid video extension."""
        valid_extensions = ('.mp4', '.avi', '.mov', '.mkv', '.wmv')
        return filename.lower().endswith(valid_extensions) 