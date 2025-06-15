import os
import shutil
from typing import Optional
from fastapi import UploadFile
import uuid

class FileHandler:
    def __init__(self, upload_dir: str = "uploads"):
        self.upload_dir = upload_dir
        os.makedirs(upload_dir, exist_ok=True)

    async def save_upload_file(self, upload_file: UploadFile) -> str:
        """Save an uploaded file and return its path"""
        try:
            # Generate unique filename
            file_extension = os.path.splitext(upload_file.filename)[1]
            unique_filename = f"{uuid.uuid4()}{file_extension}"
            file_path = os.path.join(self.upload_dir, unique_filename)

            # Save the file
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(upload_file.file, buffer)

            return file_path
        except Exception as e:
            raise Exception(f"Error saving file: {str(e)}")

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
        """Check if file is a valid video file"""
        valid_extensions = {'.mp4', '.avi', '.mov', '.mkv', '.wmv'}
        return self.get_file_extension(filename) in valid_extensions 