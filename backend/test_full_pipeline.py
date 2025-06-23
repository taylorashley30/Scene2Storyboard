#!/usr/bin/env python3
"""
Test the full pipeline including storyboard generation
"""

import requests
import json
import time
import os

def test_youtube_pipeline():
    """Test the full pipeline with a YouTube video"""
    print("🧪 Testing Full Pipeline with YouTube Video")
    print("=" * 50)
    
    # Test with a short YouTube video
    youtube_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"  # Rick Roll - short video
    
    print(f"Processing YouTube video: {youtube_url}")
    
    # Prepare the request
    payload = {
        "youtube_url": youtube_url,
        "scene_request": {
            "use_pyscenedetect": True,
            "threshold": 30.0
        }
    }
    
    try:
        # Send the request
        print("Sending request to /process/youtube...")
        response = requests.post(
            "http://localhost:8000/process/youtube",
            json=payload,
            timeout=300  # 5 minutes timeout
        )
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Video processed successfully!")
            print(f"Session ID: {result.get('session_path', 'N/A')}")
            print(f"Total scenes: {result.get('scene_metadata', {}).get('total_scenes', 0)}")
            
            # Check if storyboard was generated
            if 'storyboard_path' in result.get('scene_metadata', {}):
                print(f"✅ Storyboard generated: {result['scene_metadata']['storyboard_path']}")
                
                # Test accessing the storyboard
                session_id = os.path.basename(result['session_path'])
                storyboard_url = f"http://localhost:8000/storyboard/{session_id}"
                print(f"Storyboard URL: {storyboard_url}")
                
                # Try to access the storyboard
                storyboard_response = requests.get(storyboard_url)
                if storyboard_response.status_code == 200:
                    print("✅ Storyboard accessible via API")
                    print(f"Storyboard size: {len(storyboard_response.content)} bytes")
                else:
                    print(f"❌ Storyboard not accessible: {storyboard_response.status_code}")
            else:
                print("❌ No storyboard path in response")
            
            return result
            
        else:
            print(f"❌ Request failed with status {response.status_code}")
            print(f"Error: {response.text}")
            return None
            
    except requests.exceptions.Timeout:
        print("❌ Request timed out (video processing took too long)")
        return None
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to server. Make sure the server is running.")
        return None
    except Exception as e:
        print(f"❌ Error: {e}")
        return None

def test_storyboard_regeneration():
    """Test regenerating storyboard for an existing session"""
    print("\n🧪 Testing Storyboard Regeneration")
    print("=" * 40)
    
    # First, get list of sessions
    try:
        response = requests.get("http://localhost:8000/sessions")
        if response.status_code == 200:
            sessions = response.json().get('sessions', [])
            
            if sessions:
                # Use the first session
                session = sessions[0]
                session_id = session['session_id']
                print(f"Using session: {session_id}")
                
                # Test storyboard regeneration
                regen_response = requests.post(f"http://localhost:8000/generate-storyboard/{session_id}")
                
                if regen_response.status_code == 200:
                    result = regen_response.json()
                    print("✅ Storyboard regenerated successfully!")
                    print(f"Storyboard path: {result.get('storyboard_path', 'N/A')}")
                else:
                    print(f"❌ Storyboard regeneration failed: {regen_response.status_code}")
                    print(f"Error: {regen_response.text}")
            else:
                print("No sessions available for testing")
        else:
            print(f"Failed to get sessions: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Error testing storyboard regeneration: {e}")

def main():
    """Run the full pipeline test"""
    print("🎬 Scene2Storyboard Full Pipeline Test")
    print("=" * 60)
    
    # Test the full pipeline
    result = test_youtube_pipeline()
    
    if result:
        # Test storyboard regeneration
        test_storyboard_regeneration()
        
        print("\n🎉 Full pipeline test completed!")
        print("\nYou can now:")
        print("1. View the generated storyboard in your browser")
        print("2. Check the session folder for all generated files")
        print("3. Test the frontend to see the complete user experience")
    else:
        print("\n❌ Pipeline test failed. Check the server logs for details.")

if __name__ == "__main__":
    main() 