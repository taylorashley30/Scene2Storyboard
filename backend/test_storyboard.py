#!/usr/bin/env python3
"""
Test script for storyboard generation functionality
"""

import os
import sys
import json
from PIL import Image, ImageDraw, ImageFont

# Add the current directory to the path so we can import utils
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils.storyboard_generator import StoryboardGenerator

def create_test_frames():
    """Create some test frame images for testing"""
    test_dir = "test_frames"
    os.makedirs(test_dir, exist_ok=True)
    
    # Create 3 test frames with different colors and text
    frames = []
    colors = [(255, 0, 0), (0, 255, 0), (0, 0, 255)]  # Red, Green, Blue
    texts = ["Scene 1", "Scene 2", "Scene 3"]
    
    for i, (color, text) in enumerate(zip(colors, texts)):
        # Create a simple test image
        img = Image.new('RGB', (320, 180), color)
        draw = ImageDraw.Draw(img)
        
        # Add text to the image
        try:
            font = ImageFont.truetype("/System/Library/Fonts/Arial.ttf", 24)
        except:
            font = ImageFont.load_default()
        
        # Get text size and center it
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        x = (320 - text_width) // 2
        y = (180 - text_height) // 2
        
        draw.text((x, y), text, fill='white', font=font)
        
        # Save the frame
        frame_path = os.path.join(test_dir, f"scene_{i}.jpg")
        img.save(frame_path)
        frames.append(frame_path)
    
    return frames

def test_storyboard_generation():
    """Test the storyboard generation functionality"""
    print("Testing storyboard generation...")
    
    # Create test frames
    print("Creating test frames...")
    test_frames = create_test_frames()
    
    # Create test scene data
    test_scenes = [
        {
            "scene_number": 1,
            "frame_path": test_frames[0],
            "enhanced_caption": "A dramatic red scene with intense lighting and shadows"
        },
        {
            "scene_number": 2,
            "frame_path": test_frames[1],
            "enhanced_caption": "A peaceful green landscape with rolling hills and trees"
        },
        {
            "scene_number": 3,
            "frame_path": test_frames[2],
            "enhanced_caption": "A mysterious blue underwater scene with bubbles floating up"
        }
    ]
    
    # Initialize storyboard generator
    generator = StoryboardGenerator()
    
    # Generate storyboard
    print("Generating storyboard...")
    output_path = "test_storyboard.jpg"
    
    try:
        result_path = generator.generate_storyboard(test_scenes, output_path)
        print(f"✅ Storyboard generated successfully: {result_path}")
        
        # Check if the file exists and has reasonable size
        if os.path.exists(result_path):
            file_size = os.path.getsize(result_path)
            print(f"✅ Storyboard file size: {file_size} bytes")
            
            # Try to open the image to verify it's valid
            with Image.open(result_path) as img:
                print(f"✅ Storyboard dimensions: {img.size}")
                print(f"✅ Storyboard mode: {img.mode}")
        else:
            print("❌ Storyboard file was not created")
            
    except Exception as e:
        print(f"❌ Storyboard generation failed: {e}")
        return False
    
    # Test with different number of scenes
    print("\nTesting with different scene counts...")
    
    # Test with 1 scene
    single_scene = [test_scenes[0]]
    try:
        result_path = generator.generate_storyboard(single_scene, "test_storyboard_single.jpg")
        print(f"✅ Single scene storyboard: {result_path}")
    except Exception as e:
        print(f"❌ Single scene failed: {e}")
    
    # Test with 6 scenes (duplicate the existing ones)
    six_scenes = test_scenes + [
        {
            "scene_number": 4,
            "frame_path": test_frames[0],  # Reuse frame
            "enhanced_caption": "Another dramatic moment with intense action"
        },
        {
            "scene_number": 5,
            "frame_path": test_frames[1],  # Reuse frame
            "enhanced_caption": "A quiet moment of reflection in nature"
        },
        {
            "scene_number": 6,
            "frame_path": test_frames[2],  # Reuse frame
            "enhanced_caption": "The final scene with a surprising twist"
        }
    ]
    
    try:
        result_path = generator.generate_storyboard(six_scenes, "test_storyboard_six.jpg")
        print(f"✅ Six scene storyboard: {result_path}")
    except Exception as e:
        print(f"❌ Six scene failed: {e}")
    
    print("\n🎉 Storyboard generation test completed!")
    return True

def cleanup_test_files():
    """Clean up test files"""
    test_files = [
        "test_storyboard.jpg",
        "test_storyboard_single.jpg", 
        "test_storyboard_six.jpg"
    ]
    
    for file in test_files:
        if os.path.exists(file):
            os.remove(file)
            print(f"Cleaned up: {file}")
    
    # Clean up test frames directory
    if os.path.exists("test_frames"):
        import shutil
        shutil.rmtree("test_frames")
        print("Cleaned up: test_frames/")

if __name__ == "__main__":
    print("🧪 Storyboard Generation Test")
    print("=" * 40)
    
    success = test_storyboard_generation()
    
    if success:
        print("\n✅ All tests passed! Storyboard generation is working correctly.")
        
        # Ask if user wants to keep test files
        response = input("\nKeep test files? (y/n): ").lower().strip()
        if response != 'y':
            cleanup_test_files()
        else:
            print("Test files kept for inspection.")
    else:
        print("\n❌ Some tests failed. Check the output above for details.")
        cleanup_test_files() 