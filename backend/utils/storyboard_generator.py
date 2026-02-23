#!/usr/bin/env python3
"""
Storyboard Generator utility for creating comic-strip style layouts
"""

import os
import math
from typing import List, Dict, Tuple, Optional
from PIL import Image, ImageDraw, ImageFont
import json

from utils.panel_expander import expand_scenes_to_panels, assign_distinct_frames_to_panels, deduplicate_panel_captions

class StoryboardGenerator:
    """Class for generating comic-strip style storyboards from scene data"""

    # Max panels per page to keep each page at a viewable size (e.g. 12 = 3 rows × 4 cols)
    DEFAULT_MAX_PANELS_PER_PAGE = 12

    def __init__(self):
        """Initialize the storyboard generator"""
        self.default_font_size = 16
        self.panel_padding = 10
        # Extra space so multi-line captions don't get cut off (~6-7 lines at 16pt).
        self.caption_height = 150
        self.border_width = 2
        self._last_pdf_path: Optional[str] = None
        self._last_page_paths: List[str] = []
        
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
    
    def _create_storyboard_page(
        self,
        panels_data: List[Dict],
        page_num: int,
        total_pages: int,
        total_panels: int,
        max_width: int,
        story_arc_summary: Optional[str] = None,
    ) -> Image.Image:
        """Create a single page of the storyboard."""
        num_on_page = len(panels_data)
        cols, rows, panel_width, panel_height = self._calculate_layout(num_on_page, max_width)
        storyboard_width = cols * panel_width + (cols + 1) * self.panel_padding

        title_font = self._load_font(24)
        title = f"Storyboard - {total_panels} Scenes"
        if total_pages > 1:
            title += f" (Page {page_num}/{total_pages})"
        title_bbox = title_font.getbbox(title)
        title_height = title_bbox[3] - title_bbox[1]
        title_area_height = title_height + 2 * self.panel_padding

        if story_arc_summary and story_arc_summary.strip():
            subtitle_font = self._load_font(16)
            subtitle_lines = self._wrap_text(
                story_arc_summary.strip(),
                subtitle_font,
                storyboard_width - 2 * self.panel_padding,
            )
            line_height = subtitle_font.getbbox("Ay")[3]
            title_area_height += len(subtitle_lines) * line_height + self.panel_padding

        storyboard_height = title_area_height + rows * panel_height + (rows + 1) * self.panel_padding
        storyboard = Image.new('RGB', (storyboard_width, storyboard_height), color='white')
        draw = ImageDraw.Draw(storyboard)

        title_width = title_bbox[2] - title_bbox[0]
        title_x = (storyboard_width - title_width) // 2
        title_y = self.panel_padding
        draw.text((title_x, title_y), title, fill='black', font=title_font)

        if story_arc_summary and story_arc_summary.strip():
            subtitle_font = self._load_font(16)
            subtitle_lines = self._wrap_text(
                story_arc_summary.strip(),
                subtitle_font,
                storyboard_width - 2 * self.panel_padding,
            )
            line_height = subtitle_font.getbbox("Ay")[3]
            subtitle_y = title_y + title_height + self.panel_padding // 2
            for line in subtitle_lines:
                line_bbox = subtitle_font.getbbox(line)
                line_width = line_bbox[2] - line_bbox[0]
                line_x = (storyboard_width - line_width) // 2
                draw.text((line_x, subtitle_y), line, fill='gray', font=subtitle_font)
                subtitle_y += line_height

        for i, scene in enumerate(panels_data):
            row = i // cols
            col = i % cols
            x = col * panel_width + (col + 1) * self.panel_padding
            y = title_area_height + row * panel_height + (row + 1) * self.panel_padding
            frame_path = scene.get('frame_path', '')
            caption = scene.get('enhanced_caption', f"Scene {scene.get('scene_number', i+1)}")
            panel_img = self._create_panel(frame_path, caption, panel_width, panel_height)
            storyboard.paste(panel_img, (x, y))

        return storyboard

    def generate_storyboard(
        self,
        scenes_data: List[Dict],
        output_path: str,
        max_width: int = 1200,
        story_arc_summary: Optional[str] = None,
        max_panels_per_page: Optional[int] = None,
    ) -> str:
        """
        Generate a comic-strip style storyboard from scene data.
        For long videos, splits into multiple pages and produces a multi-page PDF.

        Args:
            scenes_data (List[Dict]): List of scene dicts with frame_path and enhanced_caption
            output_path (str): Base path (e.g. storyboard.jpg) - page 1 is saved here
            max_width (int): Maximum width per page
            story_arc_summary (Optional[str]): Optional subtitle (e.g. video title)
            max_panels_per_page (Optional[int]): Max panels per page (default 12). When exceeded, creates multiple pages.

        Returns:
            str: Path to the primary storyboard image (page 1)
        """
        if not scenes_data:
            raise ValueError("No scenes provided for storyboard generation")

        max_per_page = max_panels_per_page or self.DEFAULT_MAX_PANELS_PER_PAGE
        total_panels = len(scenes_data)
        session_dir = os.path.dirname(output_path)
        base_name = os.path.splitext(os.path.basename(output_path))[0]

        # Split panels into pages
        page_chunks: List[List[Dict]] = []
        for i in range(0, total_panels, max_per_page):
            page_chunks.append(scenes_data[i : i + max_per_page])
        total_pages = len(page_chunks)

        page_paths: List[str] = []
        for p, chunk in enumerate(page_chunks):
            page_num = p + 1
            page_img = self._create_storyboard_page(
                chunk, page_num, total_pages, total_panels, max_width, story_arc_summary
            )
            if total_pages > 1:
                page_path = os.path.join(session_dir, f"{base_name}_page_{page_num}.jpg")
            else:
                page_path = output_path
            page_img.save(page_path, 'JPEG', quality=95)
            page_paths.append(page_path)

        # Backward compat: storyboard.jpg always points to first page
        if total_pages > 1:
            import shutil
            shutil.copy(page_paths[0], output_path)

        # Create multi-page PDF when there are multiple pages
        if total_pages > 1:
            try:
                import img2pdf
                pdf_path = os.path.join(session_dir, f"{base_name}.pdf")
                with open(pdf_path, "wb") as pdf_file:
                    pdf_file.write(img2pdf.convert(page_paths))
                # Store PDF path in metadata via return - caller can persist
                self._last_pdf_path = pdf_path
                self._last_page_paths = page_paths
            except Exception as e:
                print(f"[Storyboard] Multi-page PDF creation failed: {e}")
                self._last_pdf_path = None
                self._last_page_paths = page_paths
        else:
            self._last_pdf_path = None
            self._last_page_paths = [output_path]

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
        
        # Get scenes data and optional story arc (video name)
        scenes_data = metadata.get('scenes', [])
        if not scenes_data:
            raise ValueError("No scenes found in metadata")
        story_arc_summary = metadata.get('video_name') or metadata.get('story_arc_summary')

        # Expand long captions into panels (same as pipeline)
        panels_data = expand_scenes_to_panels(scenes_data, max_caption_chars=180)
        panels_data = deduplicate_panel_captions(panels_data)
        # When panels share a scene, extract distinct frames at evenly spaced timestamps
        video_path = metadata.get("video_path")
        if video_path and os.path.exists(video_path):
            panels_data = assign_distinct_frames_to_panels(
                panels_data, video_path, session_path
            )
        
        # Generate storyboard
        output_path = os.path.join(session_path, output_filename)
        return self.generate_storyboard(
            panels_data, output_path, story_arc_summary=story_arc_summary
        ) 