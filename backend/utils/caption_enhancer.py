#!/usr/bin/env python3
"""
Caption Enhancement utility for creating clean, readable storyboard captions.
Supports optional LLM enhancement via Gemini API when GEMINI_API_KEY is set.
"""

import os
import re
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from typing import List, Dict, Optional

class CaptionEnhancer:
    """Class for enhancing captions with clean, readable formatting; optional LLM polish."""

    def __init__(self):
        """
        Initialize the caption enhancer.

        Priority of enhancement backends:
        1. Gemini (free tier via Google AI Studio) when GEMINI_API_KEY is set.
        2. Pure rule-based enhancement (no external API).
        """
        self._gemini_api_key: Optional[str] = os.environ.get("GEMINI_API_KEY") or None

        # Batch size per Gemini API request (to stay within token limits and rate limits).
        # For longer videos, scenes will be split into batches and processed sequentially.
        self._gemini_max_scenes_per_request: int = int(
            os.environ.get("GEMINI_MAX_SCENES_PER_REQUEST", "30")
        )
        # Hard stop: if a single video has more scenes than this, we won't call Gemini at all.
        # Set higher for paid tier (e.g., 200+); lower for free tier (e.g., 100).
        self._gemini_hard_scene_cap: int = int(
            os.environ.get("GEMINI_HARD_SCENE_CAP", "200")
        )
        # Delay between batches (seconds) to respect rate limits. Increase if you hit rate limits.
        self._gemini_batch_delay: float = float(
            os.environ.get("GEMINI_BATCH_DELAY", "2.0")
        )
    
    def _deduplicate_repeated_words(self, text: str) -> str:
        """
        Collapse consecutive repeated words (e.g. 'minecraft minecraft minecraft' -> 'minecraft').
        BLIP can sometimes produce repetitive output; this cleans it up.
        """
        if not text or not text.strip():
            return text
        words = text.split()
        if len(words) < 2:
            return text
        result = [words[0]]
        for w in words[1:]:
            if w.lower() != result[-1].lower():
                result.append(w)
        return " ".join(result)

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
        
        # Fix common spelling errors / typical mis-hearings
        fixes = {
            "persun": "person",
            "paren'ts": "parents", 
            "couchs": "couches",
            "on the business library": "in the business library",
            "on the": "in the",  # Common error
            "he we are": "here we are",
            "the'se": "these",
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
        
        # Clean the visual caption (deduplicate repeated words from BLIP)
        clean_visual = self._deduplicate_repeated_words(visual_caption.strip())
        if clean_visual:
            # Capitalize first letter
            clean_visual = clean_visual[0].upper() + clean_visual[1:]
        
        # Combine visual + dialogue in a compact way, good for short clips.
        has_visual = bool(clean_visual)
        has_transcript = bool(clean_transcript) and len(clean_transcript) > 5

        # Shorten very long dialogue so it doesn't dominate the panel.
        if has_transcript:
            max_chars = 80
            if len(clean_transcript) > max_chars:
                # Truncate on a word boundary if possible.
                snippet = clean_transcript[:max_chars]
                last_space = snippet.rfind(" ")
                if last_space > 0:
                    snippet = snippet[:last_space]
                clean_transcript = snippet.rstrip(" .") + "..."

        if has_visual and has_transcript:
            # Visual-first, then a brief dialogue snippet in quotes so it's clear it's spoken.
            return f'{clean_visual} — "{clean_transcript}"'
        if has_visual:
            return clean_visual
        if has_transcript:
            return clean_transcript
        # Fallback
        return f"Scene {scene_number}"

    def _gemini_enhance_captions_batch(
        self, scenes: List[Dict]
    ) -> Optional[List[str]]:
        """
        Use Gemini to enhance captions for scenes, splitting into batches if needed.

        For videos with many scenes, splits into batches and processes sequentially
        with delays to respect rate limits. Returns a list of caption strings matching
        the input scenes order, or None if Gemini is unavailable or fails.
        """
        if not self._gemini_api_key or not self._gemini_api_key.strip():
            return None

        num_scenes = len(scenes)
        if num_scenes == 0:
            return []

        # Hard cap: refuse if video has too many scenes (to avoid excessive API usage).
        if num_scenes > self._gemini_hard_scene_cap:
            print(
                f"Gemini enhancement skipped: {num_scenes} scenes exceeds hard cap "
                f"{self._gemini_hard_scene_cap}. Increase GEMINI_HARD_SCENE_CAP if needed."
            )
            return None

        try:
            from google import genai
            import time
        except ImportError:
            print("google-genai is not installed; skipping Gemini enhancement.")
            return None

        try:
            client = genai.Client(api_key=self._gemini_api_key)
            model_name = os.environ.get("GEMINI_MODEL", "gemini-2.0-flash")

            # Split scenes into batches if needed.
            batch_size = self._gemini_max_scenes_per_request
            num_batches = (num_scenes + batch_size - 1) // batch_size

            if num_batches > 1:
                print(
                    f"[Gemini] Processing {num_scenes} scenes in {num_batches} batches "
                    f"(max {batch_size} per batch)..."
                )
            else:
                print(f"[Gemini] Processing {num_scenes} scenes...")

            all_captions: List[str] = []

            for batch_idx in range(num_batches):
                start_idx = batch_idx * batch_size
                end_idx = min(start_idx + batch_size, num_scenes)
                batch_scenes = scenes[start_idx:end_idx]

                # Build prompt for this batch.
                scene_descriptions = []
                for scene in batch_scenes:
                    num = scene.get("scene_number", start_idx + len(scene_descriptions) + 1)
                    visual = self._deduplicate_repeated_words((scene.get("caption") or "").strip())
                    transcript = (scene.get("transcript") or "").strip()
                    scene_descriptions.append(
                        f"Scene {num}:\n"
                        f"Visual: {visual or 'None'}\n"
                        f"Transcript: {transcript or 'None'}"
                    )

                joined = "\n\n".join(scene_descriptions)

                system_instructions = (
                    "You are a storyboard caption editor. For each scene, you will be given "
                    "a visual description and a rough transcript (may contain ASR errors).\n\n"
                    "Task:\n"
                    "- For every scene, output exactly ONE short caption line.\n"
                    "- Format each line strictly as:\n"
                    '  Scene <N>: <Visual description> — "Dialogue."\n'
                    "- Fix obvious transcription errors while keeping the meaning.\n"
                    "- Make captions concise and suitable for a comic panel.\n"
                    "- Output one line per scene in order, no extra text before or after."
                )

                prompt = f"{system_instructions}\n\nScenes:\n{joined}\n\nCaptions:"

                def _call_api():
                    response = client.models.generate_content(
                        model=model_name,
                        contents=prompt,
                    )
                    text = (getattr(response, "text", None) or "").strip()
                    if not text:
                        return None
                    lines = [line.strip() for line in text.splitlines() if line.strip()]
                    return lines

                gemini_timeout = int(os.environ.get("GEMINI_REQUEST_TIMEOUT", "90"))
                executor = ThreadPoolExecutor(max_workers=1)
                future = executor.submit(_call_api)
                try:
                    batch_result = future.result(timeout=gemini_timeout)
                except FuturesTimeoutError:
                    executor.shutdown(wait=False)
                    print(
                        f"[Gemini] Batch {batch_idx + 1}/{num_batches} timed out after {gemini_timeout}s; "
                        "using rule-based captions for remaining scenes."
                    )
                    # Fill remaining with empty strings so we can still return partial results
                    all_captions.extend([""] * (num_scenes - len(all_captions)))
                    return all_captions if all_captions else None
                executor.shutdown(wait=True)

                if batch_result is None:
                    print(f"[Gemini] Batch {batch_idx + 1}/{num_batches} returned no results.")
                    all_captions.extend([""] * len(batch_scenes))
                else:
                    # Ensure we got the right number of captions for this batch.
                    while len(batch_result) < len(batch_scenes):
                        batch_result.append("")
                    all_captions.extend(batch_result[:len(batch_scenes)])

                # Delay between batches to respect rate limits (except after the last batch).
                if batch_idx < num_batches - 1 and self._gemini_batch_delay > 0:
                    time.sleep(self._gemini_batch_delay)

            print(f"[Gemini] Done. Enhanced {len([c for c in all_captions if c])} captions.")
            return all_captions[:num_scenes]
        except Exception as e:
            print(f"Gemini caption enhancement failed: {e}; falling back to non-Gemini paths.")
            return None

    def enhance_caption(self, visual_caption: str, transcript: str, scene_number: int) -> str:
        """
        Enhance a caption for storyboard display.
        When Gemini is configured and within conservative limits, captions are enhanced
        in batch mode via enhance_scene_captions. Otherwise falls back to rule-based
        enhancement only (no paid API usage).
        """
        try:
            return self._create_storyboard_caption(visual_caption, transcript, scene_number)
        except Exception as e:
            print(f"Error enhancing caption for scene {scene_number}: {e}")
            return visual_caption if visual_caption else f"Scene {scene_number}"
    
    def enhance_scene_captions(self, scenes_data: List[Dict]) -> List[Dict]:
        """
        Enhance captions for all scenes in a video
        
        Args:
            scenes_data (List[Dict]): List of scene dictionaries with 'caption' and 'transcript' fields
            
        Returns:
            List[Dict]: Updated scenes with enhanced captions
        """
        if not scenes_data:
            return []

        # Try Gemini batch enhancement first, staying within conservative limits.
        gemini_captions: Optional[List[str]] = None
        if self._gemini_api_key and self._gemini_api_key.strip():
            gemini_captions = self._gemini_enhance_captions_batch(scenes_data)

        enhanced_scenes: List[Dict] = []

        for idx, scene in enumerate(scenes_data):
            scene_number = scene.get("scene_number", idx + 1)
            visual_caption = scene.get("caption", "")
            transcript = scene.get("transcript", "")

            if gemini_captions is not None and idx < len(gemini_captions):
                candidate = gemini_captions[idx].strip()
                if candidate:
                    enhanced_caption = candidate
                else:
                    enhanced_caption = self.enhance_caption(
                        visual_caption, transcript, scene_number
                    )
            else:
                enhanced_caption = self.enhance_caption(
                    visual_caption, transcript, scene_number
                )

            enhanced_scene = scene.copy()
            enhanced_scene["enhanced_caption"] = enhanced_caption
            enhanced_scenes.append(enhanced_scene)

        return enhanced_scenes 