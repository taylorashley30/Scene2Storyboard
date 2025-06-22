#!/usr/bin/env python3
"""
Caption Enhancement utility for creating clean, readable storyboard captions
"""

import re
from typing import List, Dict, Optional

class CaptionEnhancer:
    """Class for enhancing captions with clean, readable formatting"""
    
    def __init__(self):
        """Initialize the caption enhancer"""
        pass
    
    def _clean_transcript(self, transcript: str) -> str:
        """
        Clean up transcript text for better readability
        
        Args:
            transcript (str): Raw transcript text
            
        Returns:
            str: Cleaned transcript
        """
        if not transcript or transcript.strip() == "":
            return ""
        
        # Clean up common transcription errors
        transcript = transcript.strip()
        
        # Fix common spelling errors
        fixes = {
            "persun": "person",
            "paren'ts": "parents", 
            "couchs": "couches",
            "on the business library": "in the business library",
            "on the": "in the",  # Common error
        }
        
        for error, correction in fixes.items():
            transcript = transcript.replace(error, correction)
        
        # Remove extra whitespace
        transcript = re.sub(r'\s+', ' ', transcript)
        
        # Capitalize first letter
        if transcript:
            transcript = transcript[0].upper() + transcript[1:]
        
        return transcript
    
    def _create_storyboard_caption(self, visual_caption: str, transcript: str, scene_number: int) -> str:
        """
        Create a clean storyboard caption combining visual and audio elements
        
        Args:
            visual_caption (str): BLIP-generated visual description
            transcript (str): Whisper-generated audio transcript
            scene_number (int): Scene number for context
            
        Returns:
            str: Clean storyboard caption
        """
        # Clean the transcript
        clean_transcript = self._clean_transcript(transcript)
        
        # Clean the visual caption
        clean_visual = visual_caption.strip()
        if clean_visual:
            # Capitalize first letter
            clean_visual = clean_visual[0].upper() + clean_visual[1:]
        
        # Create the caption based on content
        if clean_transcript and len(clean_transcript) > 5:
            # If there's substantial dialogue, use it as the primary caption
            return clean_transcript
        elif clean_visual:
            # If no dialogue, use the visual description
            return clean_visual
        else:
            # Fallback
            return f"Scene {scene_number}"
    
    def enhance_caption(self, visual_caption: str, transcript: str, scene_number: int) -> str:
        """
        Enhance a caption for storyboard display
        
        Args:
            visual_caption (str): BLIP-generated visual description
            transcript (str): Whisper-generated audio transcript
            scene_number (int): Scene number for context
            
        Returns:
            str: Enhanced storyboard caption
        """
        try:
            return self._create_storyboard_caption(visual_caption, transcript, scene_number)
        except Exception as e:
            print(f"Error enhancing caption for scene {scene_number}: {e}")
            # Fallback to simple visual caption
            return visual_caption if visual_caption else f"Scene {scene_number}"
    
    def enhance_scene_captions(self, scenes_data: List[Dict]) -> List[Dict]:
        """
        Enhance captions for all scenes in a video
        
        Args:
            scenes_data (List[Dict]): List of scene dictionaries with 'caption' and 'transcript' fields
            
        Returns:
            List[Dict]: Updated scenes with enhanced captions
        """
        enhanced_scenes = []
        
        for scene in scenes_data:
            scene_number = scene.get('scene_number', 1)
            visual_caption = scene.get('caption', '')
            transcript = scene.get('transcript', '')
            
            # Enhance the caption
            enhanced_caption = self.enhance_caption(visual_caption, transcript, scene_number)
            
            # Create updated scene data
            enhanced_scene = scene.copy()
            enhanced_scene['enhanced_caption'] = enhanced_caption
            
            enhanced_scenes.append(enhanced_scene)
        
        return enhanced_scenes 