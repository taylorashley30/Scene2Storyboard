#!/usr/bin/env python3
"""
Storyboard Generator utility for creating comic-strip style layouts
"""

import os
import math
from typing import List, Dict, Tuple, Optional
from PIL import Image, ImageDraw, ImageFont
import json

class StoryboardGenerator:
    """Class for generating comic-strip style storyboards from scene data"""
    
    def __init__(self):
        """Initialize the storyboard generator"""
        self.default_font_size = 16
        self.panel_padding = 10
        self.caption_height = 60
        self.border_width = 2
        
    def _load_font(self, size: int = None) -> ImageFont.FreeTypeFont:
        """
        Load a font for caption text
        
        Args:
            size (int): Font size (default: self.default_font_size)
            
        Returns:
            ImageFont.FreeTypeFont: Loaded font
        """
        try:
            # Try to load a system font
            font_size = size or self.default_font_size
            return ImageFont.truetype("/System/Library/Fonts/Arial.ttf", font_size)
        except:
            try:
                # Fallback to another common font
                return ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", font_size)
            except:
                # Use default font
                return ImageFont.load_default()
    
    def _calculate_layout(self, num_scenes: int, max_width: int = 1200) -> Tuple[int, int, int, int]:
        """
        Calculate the optimal grid layout for the storyboard
        
        Args:
            num_scenes (int): Number of scenes to display
            max_width (int): Maximum width of the storyboard
            
        Returns:
            Tuple[int, int, int, int]: (cols, rows, panel_width, panel_height)
        """
        # Calculate optimal number of columns based on aspect ratio
        # For a comic strip, we want more columns than rows
        if num_scenes <= 3:
            cols = num_scenes
        elif num_scenes <= 6:
            cols = 3
        elif num_scenes <= 9:
            cols = 3
        else:
            cols = 4
        
        rows = math.ceil(num_scenes / cols)
        
        # Calculate panel dimensions
        panel_width = (max_width - (cols + 1) * self.panel_padding) // cols
        panel_height = int(panel_width * 0.6) + self.caption_height  # 16:9 aspect ratio + caption
        
        return cols, rows, panel_width, panel_height
    
    def _wrap_text(self, text: str, font: ImageFont.FreeTypeFont, max_width: int) -> List[str]:
        """
        Wrap text to fit within a given width
        
        Args:
            text (str): Text to wrap
            font (ImageFont.FreeTypeFont): Font to use for measurement
            max_width (int): Maximum width for each line
            
        Returns:
            List[str]: List of wrapped text lines
        """
        words = text.split()
        lines = []
        current_line = ""
        
        for word in words:
            test_line = current_line + " " + word if current_line else word
            bbox = font.getbbox(test_line)
            text_width = bbox[2] - bbox[0]
            
            if text_width <= max_width:
                current_line = test_line
            else:
                if current_line:
                    lines.append(current_line)
                current_line = word
        
        if current_line:
            lines.append(current_line)
        
        return lines if lines else [text]
    
    def _create_panel(self, frame_path: str, caption: str, panel_width: int, panel_height: int) -> Image.Image:
        """
        Create a single storyboard panel with frame and caption
        
        Args:
            frame_path (str): Path to the scene frame image
            caption (str): Caption text for the panel
            panel_width (int): Width of the panel
            panel_height (int): Height of the panel
            
        Returns:
            Image.Image: Panel image with frame and caption
        """
        # Create panel canvas
        panel = Image.new('RGB', (panel_width, panel_height), color='white')
        draw = ImageDraw.Draw(panel)
        
        # Load and resize frame
        try:
            frame = Image.open(frame_path)
            frame_width = panel_width - 2 * self.panel_padding
            frame_height = panel_height - self.caption_height - 2 * self.panel_padding
            
            # Resize frame maintaining aspect ratio
            frame.thumbnail((frame_width, frame_height), Image.Resampling.LANCZOS)
            
            # Center the frame in the panel
            frame_x = (panel_width - frame.width) // 2
            frame_y = self.panel_padding
            panel.paste(frame, (frame_x, frame_y))
            
        except Exception as e:
            # If frame loading fails, create a placeholder
            placeholder_color = (200, 200, 200)
            draw.rectangle([self.panel_padding, self.panel_padding, 
                          panel_width - self.panel_padding, 
                          panel_height - self.caption_height - self.panel_padding], 
                         fill=placeholder_color)
            draw.text((panel_width // 2, (panel_height - self.caption_height) // 2), 
                     "Frame not found", fill='black', anchor='mm')
        
        # Add border around panel
        draw.rectangle([0, 0, panel_width - 1, panel_height - 1], 
                      outline='black', width=self.border_width)
        
        # Add caption
        if caption:
            font = self._load_font()
            caption_area_width = panel_width - 2 * self.panel_padding
            caption_area_height = self.caption_height - 2 * self.panel_padding
            
            # Wrap caption text
            wrapped_lines = self._wrap_text(caption, font, caption_area_width)
            
            # Calculate text position
            line_height = font.getbbox("Ay")[3]  # Approximate line height
            total_text_height = len(wrapped_lines) * line_height
            start_y = panel_height - self.caption_height + (caption_area_height - total_text_height) // 2
            
            # Draw each line of caption
            for i, line in enumerate(wrapped_lines):
                y = start_y + i * line_height
                bbox = font.getbbox(line)
                text_width = bbox[2] - bbox[0]
                x = (panel_width - text_width) // 2
                draw.text((x, y), line, fill='black', font=font)
        
        return panel
    
    def generate_storyboard(self, scenes_data: List[Dict], output_path: str, 
                          max_width: int = 1200) -> str:
        """
        Generate a comic-strip style storyboard from scene data
        
        Args:
            scenes_data (List[Dict]): List of scene dictionaries with frame_path and enhanced_caption
            output_path (str): Path to save the generated storyboard
            max_width (int): Maximum width of the storyboard
            
        Returns:
            str: Path to the generated storyboard image
        """
        if not scenes_data:
            raise ValueError("No scenes provided for storyboard generation")
        
        # Calculate layout
        num_scenes = len(scenes_data)
        cols, rows, panel_width, panel_height = self._calculate_layout(num_scenes, max_width)
        
        # Calculate storyboard dimensions
        storyboard_width = cols * panel_width + (cols + 1) * self.panel_padding
        storyboard_height = rows * panel_height + (rows + 1) * self.panel_padding
        
        # Create storyboard canvas
        storyboard = Image.new('RGB', (storyboard_width, storyboard_height), color='white')
        
        # Add title
        draw = ImageDraw.Draw(storyboard)
        title_font = self._load_font(24)
        title = f"Storyboard - {num_scenes} Scenes"
        title_bbox = title_font.getbbox(title)
        title_width = title_bbox[2] - title_bbox[0]
        title_x = (storyboard_width - title_width) // 2
        draw.text((title_x, self.panel_padding), title, fill='black', font=title_font)
        
        # Create and place panels
        for i, scene in enumerate(scenes_data):
            row = i // cols
            col = i % cols
            
            # Calculate panel position
            x = col * panel_width + (col + 1) * self.panel_padding
            y = row * panel_height + (row + 1) * self.panel_padding + 40  # Extra space for title
            
            # Get scene data
            frame_path = scene.get('frame_path', '')
            caption = scene.get('enhanced_caption', f"Scene {scene.get('scene_number', i+1)}")
            
            # Create panel
            panel = self._create_panel(frame_path, caption, panel_width, panel_height)
            
            # Paste panel onto storyboard
            storyboard.paste(panel, (x, y))
        
        # Save storyboard
        storyboard.save(output_path, 'JPEG', quality=95)
        
        return output_path
    
    def generate_storyboard_from_session(self, session_path: str, output_filename: str = "storyboard.jpg") -> str:
        """
        Generate storyboard from a processing session
        
        Args:
            session_path (str): Path to the session directory
            output_filename (str): Name of the output file
            
        Returns:
            str: Path to the generated storyboard
        """
        # Load metadata
        metadata_path = os.path.join(session_path, "metadata.json")
        if not os.path.exists(metadata_path):
            raise FileNotFoundError(f"Metadata not found at {metadata_path}")
        
        with open(metadata_path, 'r') as f:
            metadata = json.load(f)
        
        # Get scenes data
        scenes_data = metadata.get('scenes', [])
        if not scenes_data:
            raise ValueError("No scenes found in metadata")
        
        # Generate storyboard
        output_path = os.path.join(session_path, output_filename)
        return self.generate_storyboard(scenes_data, output_path) 