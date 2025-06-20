#!/usr/bin/env python3
"""
Test script for the Scene2Storyboard API endpoints
"""

import requests
import json
import os
from pathlib import Path

# API base URL
BASE_URL = "http://localhost:8000"

def test_health_endpoint():
    """Test the health check endpoint"""
    print("Testing health endpoint...")
    response = requests.get(f"{BASE_URL}/health")
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    print()

def test_sessions_endpoint():
    """Test the sessions list endpoint"""
    print("Testing sessions endpoint...")
    response = requests.get(f"{BASE_URL}/sessions")
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    print()

def test_file_upload(video_path):
    """Test file upload with scene detection"""
    if not os.path.exists(video_path):
        print(f"Video file not found: {video_path}")
        return None
    
    print(f"Testing file upload with: {video_path}")
    
    # Prepare the file upload
    with open(video_path, 'rb') as f:
        files = {'file': (os.path.basename(video_path), f, 'video/mp4')}
        data = {
            'use_pyscenedetect': 'true',
            'video_name': os.path.basename(video_path)
        }
        
        response = requests.post(f"{BASE_URL}/process/upload", files=files, data=data)
    
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        result = response.json()
        print(f"Success! Session created.")
        print(f"Video info: {result.get('video_info', {})}")
        print(f"Total scenes: {result.get('scene_metadata', {}).get('total_scenes', 0)}")
        print(f"Session path: {result.get('scene_metadata', {}).get('session_path', '')}")
        return result
    else:
        print(f"Error: {response.text}")
        return None

def test_youtube_processing(youtube_url, video_name="Test Video"):
    """Test YouTube URL processing with yt-dlp"""
    print(f"Testing YouTube processing with: {youtube_url}")
    
    data = {
        "video_input": {"youtube_url": youtube_url},
        "scene_request": {
            "use_pyscenedetect": True,
            "video_name": video_name
        }
    }
    
    response = requests.post(f"{BASE_URL}/process/youtube", json=data)
    
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        result = response.json()
        print(f"Success! Session created.")
        print(f"Video info: {result.get('video_info', {})}")
        print(f"Total scenes: {result.get('scene_metadata', {}).get('total_scenes', 0)}")
        return result
    else:
        print(f"Error: {response.text}")
        return None

def test_scene_info(session_id):
    """Test getting scene information"""
    print(f"Testing scene info for session: {session_id}")
    
    response = requests.get(f"{BASE_URL}/scenes/{session_id}")
    
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        result = response.json()
        print(f"Scene info retrieved successfully!")
        print(f"Total scenes: {result.get('total_scenes', 0)}")
        print(f"Video name: {result.get('video_name', 'Unknown')}")
        
        # Print scene details
        for scene in result.get('scenes', []):
            print(f"  Scene {scene['scene_number']}: {scene['start_time']:.2f}s - {scene['end_time']:.2f}s")
        
        return result
    else:
        print(f"Error: {response.text}")
        return None

def main():
    """Main test function"""
    print("Scene2Storyboard API Test Script")
    print("=" * 50)
    
    # Test health endpoint
    test_health_endpoint()
    
    # Test sessions endpoint (should be empty initially)
    test_sessions_endpoint()
    
    # Test file upload with the existing video in uploads folder
    video_path = "uploads/f7c09741-cf48-46c4-8c7d-d7e1892eacaa.mp4"
    if os.path.exists(video_path):
        print(f"Found video file: {video_path}")
        result = test_file_upload(video_path)
        if result:
            # Test getting scene info
            session_path = result.get('scene_metadata', {}).get('session_path', '')
            if session_path:
                session_id = os.path.basename(session_path)
                test_scene_info(session_id)
    else:
        print(f"Video file not found: {video_path}")
        print("Looking for any video files in uploads folder...")
        
        # Look for any video files in uploads folder
        uploads_dir = "uploads"
        if os.path.exists(uploads_dir):
            for file in os.listdir(uploads_dir):
                if file.lower().endswith(('.mp4', '.avi', '.mov', '.mkv')):
                    video_path = os.path.join(uploads_dir, file)
                    print(f"Found video file: {video_path}")
                    result = test_file_upload(video_path)
                    if result:
                        session_path = result.get('scene_metadata', {}).get('session_path', '')
                        if session_path:
                            session_id = os.path.basename(session_path)
                            test_scene_info(session_id)
                    break
    
    # Test YouTube processing with yt-dlp (should work better now)
    print("\nTesting YouTube processing with yt-dlp...")
    test_youtube_processing(
        "https://www.youtube.com/watch?v=jNQXAC9IVRw", 
        "Me at the zoo"
    )
    
    # Test sessions endpoint again (should show any created sessions)
    print("\nFinal sessions list:")
    test_sessions_endpoint()

if __name__ == "__main__":
    main() 