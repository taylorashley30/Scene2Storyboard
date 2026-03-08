#!/usr/bin/env python3
"""
Caption Enhancement utility for creating clean, readable storyboard captions.
Supports optional LLM enhancement via Gemini API when GEMINI_API_KEY is set.
"""

import json
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
        # Use global understanding pass when True (correct transcripts, correct captions, then produce final captions).
        self._use_global_caption_pass: bool = os.environ.get(
            "S2S_USE_GLOBAL_CAPTION_PASS", "true"
        ).lower() in ("true", "1", "yes")
        # Fetch additional context from web (e.g. character names, story context). Optional; disable to avoid external requests.
        self._use_web_context: bool = os.environ.get(
            "S2S_USE_WEB_CONTEXT", "false"
        ).lower() in ("true", "1", "yes")
        # When true, Gemini is allowed to summarize/condense dialogue and drop filler,
        # keeping only the key actions/ideas instead of preserving every word.
        self._summarize_captions: bool = os.environ.get(
            "S2S_SUMMARIZE_CAPTIONS", "false"
        ).lower() in ("true", "1", "yes")

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
        
        # Combine visual + dialogue: dialogue-first format for narrative flow.
        has_visual = bool(clean_visual)
        has_transcript = bool(clean_transcript) and len(clean_transcript) > 5

        # Preserve words: only truncate very long dialogue (panel wraps; 200 chars is reasonable).
        if has_transcript:
            max_chars = 200
            if len(clean_transcript) > max_chars:
                snippet = clean_transcript[:max_chars]
                last_space = snippet.rfind(" ")
                if last_space > 0:
                    snippet = snippet[:last_space]
                clean_transcript = snippet.rstrip(" .") + "..."

        if has_visual and has_transcript:
            # Dialogue-first: spoken content leads, visual anchor follows.
            return f'"{clean_transcript}" — {clean_visual}'
        if has_visual:
            return clean_visual
        if has_transcript:
            return clean_transcript
        # Fallback
        return f"Scene {scene_number}"

    def _is_cooking_video(self, video_context: Optional[Dict]) -> bool:
        """Heuristic: video appears to be cooking/baking from title or description."""
        if not video_context:
            return False
        combined = " ".join(
            filter(None, [
                video_context.get("video_name") or "",
                video_context.get("description") or "",
            ])
        ).lower()
        keywords = (
            "bake", "baking", "brownie", "recipe", "cook", "cooking", "food", "chef",
            "kitchen", "ingredients", "whisk", "mix", "oven", "pan", "butter", "chocolate",
            "dinner", "lunch", "breakfast", "meal", "tutorial", "how to make"
        )
        return any(kw in combined for kw in keywords)

    def _get_cooking_domain_instructions(self) -> str:
        """Instructions for cooking/baking videos: use standard terminology, fix common errors."""
        return (
            "\nCOOKING/BAKING CONTEXT: Use standard kitchen and baking terminology. "
            "Correct common ASR and vision model errors: 'A-B-A pan' or 'inline pan' → '8x8 pan' "
            "or 'square baking pan'; 'greased inline' → 'greased and lined'; '8 by 8' is fine. "
            "Prefer standard terms: 8x8, 9x13, loaf pan, sheet pan, etc. "
            "If ASR contains odd tool phrases (e.g. 'no-knife') in a cooking context, interpret as "
            "'no special tools' / 'no gnocchi board needed' rather than literally mentioning a knife."
        )

    def _strip_scene_prefix(self, caption: str) -> str:
        """Remove 'Scene N:' prefix from caption if present (for compatibility)."""
        if not caption or not caption.strip():
            return caption
        stripped = re.sub(r'^Scene\s+\d+\s*:\s*', '', caption.strip(), flags=re.IGNORECASE)
        return stripped.strip() or caption

    def _fetch_context_from_web(
        self, video_name: str, video_description: Optional[str] = None
    ) -> Optional[str]:
        """
        Fetch interpretive context from the web (e.g., character names, story context).
        Use only for interpretation — never add information not in the video.
        Returns a short summary or None if unavailable.
        """
        try:
            import urllib.request
            import urllib.parse
            query = (video_name or "").strip()
            if video_description:
                # Use first 50 chars of description to enrich search
                query = f"{query} {video_description[:80].strip()}"
            if not query or len(query) < 5:
                return None
            # Simple search URL (DuckDuckGo HTML)
            safe_query = urllib.parse.quote_plus(query[:100])
            url = f"https://html.duckduckgo.com/html/?q={safe_query}"
            req = urllib.request.Request(url, headers={"User-Agent": "Scene2Storyboard/1.0"})
            with urllib.request.urlopen(req, timeout=5) as resp:
                html = resp.read().decode("utf-8", errors="ignore")
            # Extract snippet from first result (simple heuristic)
            snip = re.search(r'<a[^>]+class="result__snippet"[^>]*>([^<]+)</a>', html)
            if snip:
                text = re.sub(r"<[^>]+>", "", snip.group(1))
                return (text.strip()[:500] or None) if text.strip() else None
            return None
        except Exception as e:
            print(f"[CaptionEnhancer] Web context fetch failed: {e}")
            return None

    def _gemini_correct_transcripts_batch(
        self, scenes: List[Dict]
    ) -> Optional[List[str]]:
        """Pass 1: Correct ASR errors in all transcripts. Returns list of corrected strings."""
        if not self._gemini_api_key or not scenes:
            return None
        try:
            from google import genai
        except ImportError:
            return None
        try:
            client = genai.Client(api_key=self._gemini_api_key)
            model_name = os.environ.get("GEMINI_MODEL", "gemini-2.0-flash")
            lines = []
            for s in scenes:
                num = s.get("scene_number", len(lines) + 1)
                t = (s.get("transcript") or "").strip()
                lines.append(f"Scene {num}: {t or '[no speech]'}")
            joined = "\n".join(lines)
            prompt = (
                "Fix ASR (speech-to-text) errors in these scene transcripts. "
                "Preserve the original words and meaning. Fix spelling and grammar only. "
                "Output one corrected line per scene in the same order, format: Scene N: <corrected transcript>. "
                "Do not add or remove content.\n\n" + joined
            )
            response = client.models.generate_content(model=model_name, contents=prompt)
            text = (getattr(response, "text", None) or "").strip()
            if not text:
                return None
            corrected = []
            for line in text.splitlines():
                line = line.strip()
                m = re.match(r"^Scene\s*\d+\s*[:\-]\s*(.*)", line, re.IGNORECASE)
                if m:
                    corrected.append(m.group(1).strip())
                elif line:
                    corrected.append(line)
            if len(corrected) >= len(scenes):
                return corrected[: len(scenes)]
            return None
        except Exception as e:
            print(f"[Gemini] Transcript correction failed: {e}")
            return None

    def _gemini_correct_captions_batch(
        self, scenes: List[Dict]
    ) -> Optional[List[str]]:
        """Pass 2: Fix BLIP hallucinations, repetition, irrelevant descriptions. Returns list of corrected captions."""
        if not self._gemini_api_key or not scenes:
            return None
        try:
            from google import genai
        except ImportError:
            return None
        try:
            client = genai.Client(api_key=self._gemini_api_key)
            model_name = os.environ.get("GEMINI_MODEL", "gemini-2.0-flash")
            lines = []
            for s in scenes:
                num = s.get("scene_number", len(lines) + 1)
                cap = self._deduplicate_repeated_words((s.get("caption") or "").strip())
                lines.append(f"Scene {num}: {cap or 'None'}")
            joined = "\n".join(lines)
            prompt = (
                "These are BLIP image captions that may have repetition (e.g. 'minecraft minecraft'), "
                "hallucinations, or irrelevant descriptions. Clean them: remove repetition, fix obvious "
                "misidentifications. Output one line per scene in the same order, format: Scene N: <corrected caption>. "
                "Keep captions short and factual. Do not add content not in the original.\n\n" + joined
            )
            response = client.models.generate_content(model=model_name, contents=prompt)
            text = (getattr(response, "text", None) or "").strip()
            if not text:
                return None
            corrected = []
            for line in text.splitlines():
                line = line.strip()
                m = re.match(r"^Scene\s*\d+\s*[:\-]\s*(.*)", line, re.IGNORECASE)
                if m:
                    corrected.append(m.group(1).strip())
                elif line:
                    corrected.append(line)
            if len(corrected) >= len(scenes):
                return corrected[: len(scenes)]
            return None
        except Exception as e:
            print(f"[Gemini] Caption correction failed: {e}")
            return None

    def _gemini_produce_final_captions(
        self,
        corrected_transcripts: List[str],
        corrected_captions: List[str],
        video_context: Optional[Dict] = None,
        web_context: Optional[str] = None,
    ) -> Optional[List[str]]:
        """
        Pass 4: Global understanding. Given ALL corrected transcripts and captions,
        produce final enhanced captions with full narrative context.
        Uses web context only for interpretation (character names, correcting misidentifications).
        Does NOT add information not in the video.
        """
        if not self._gemini_api_key:
            return None
        n = len(corrected_transcripts)
        if n != len(corrected_captions) or n == 0:
            return None
        try:
            from google import genai
        except ImportError:
            return None
        try:
            client = genai.Client(api_key=self._gemini_api_key)
            model_name = os.environ.get("GEMINI_MODEL", "gemini-2.0-flash")
            lines = []
            for i in range(n):
                t = (corrected_transcripts[i] or "").strip()
                v = (corrected_captions[i] or "").strip()
                transcript_label = "Transcript: [no speech]" if not t else f"Transcript: {t}"
                lines.append(f"Scene {i + 1}:\n{transcript_label}\nVisual: {v or 'None'}")
            joined = "\n\n".join(lines)
            ctx = ""
            if video_context:
                vn = video_context.get("video_name", "").strip()
                vd = (video_context.get("description") or "").strip()
                if vn:
                    ctx += f"Video title: {vn}\n"
                if vd:
                    ctx += f"Description: {vd[:300]}\n"
            if web_context:
                ctx += f"Additional context (use ONLY to interpret/correct, e.g. character names, fixing misidentifications): {web_context[:400]}\n"
            ctx += (
                "\nCRITICAL: Do NOT add any information that did not happen in the video. "
                "Use web context only to interpret (e.g. correct 'naked woman' to 'Titan' if the video is Attack on Titan). "
                "Never invent plot, dialogue, or events.\n"
            )
            cooking_block = ""
            if self._is_cooking_video(video_context):
                cooking_block = self._get_cooking_domain_instructions()

            if self._summarize_captions:
                # Compact / summarized captions: keep key actions & ideas, drop filler.
                instructions = (
                    "You are a storyboard caption editor. Create concise captions that still tell the story clearly.\n\n"
                    "SUMMARIZE: Combine repetitive phrases and filler into a clearer, shorter narration. "
                    "Remove filler words, side comments, jokes, and meta-commentary (e.g. talking about being tired, why a tool is used, "
                    "or complaining about the process) unless they are important to understanding the action. "
                    "Drop repeated exclamations like 'wow, wow, wow' after the first meaningful reaction.\n\n"
                    "AVOID REPETITION: Do not repeat the same instruction in consecutive scenes. "
                    "If a step was already stated in the previous scene, make the next caption reflect progress, result, or a new detail.\n\n"
                    "KEEP: important actions, decisions, and outcomes. For cooking/baking, keep the core steps, ingredient names, "
                    "important quantities, temperatures, and timing if mentioned. It's OK to merge several spoken sentences into "
                    "1–2 well-phrased sentences per caption.\n\n"
                    "When there IS dialogue: Format \"<Dialogue>\" — <short visual anchor>. "
                    "Use a summarized version of the dialogue that still preserves the key idea, not every word. "
                    "The visual anchor should be brief (e.g. 'whisking vigorously', 'folding in chocolate chips').\n\n"
                    "When there is NO dialogue (transcript is empty, None, or [no speech]): "
                    "Output ONLY a descriptive visual/action caption. NEVER include 'no speech', '[no speech]', or similar. "
                    "Use the full narrative context (video title, previous scenes) to infer what the scene shows.\n\n"
                    "Output one line per scene in order, no extra text before or after."
                )
            else:
                # Original high-fidelity mode: preserve all transcript content.
                instructions = (
                    "You are a storyboard caption editor. Create captions that flow as a narrative.\n\n"
                    "CRITICAL - PRESERVE ORIGINAL CONTENT: Do NOT condense, summarize, or shorten the transcript. "
                    "Include ALL of the spoken content. Original content cannot be missed. Fix ASR errors (e.g. evything->everything) "
                    "and grammar only—keep every idea, example, and explanation. Long captions are fine; they will be split automatically.\n\n"
                    "When there IS dialogue: Format \"<Dialogue>\" — <short visual anchor>. "
                    "Put the FULL transcript in quotes. When the visual describes a character expression (e.g. mouth open) and the transcript is dialogue, "
                    "infer the ACTION (e.g. screaming, commanding) in the visual anchor, not the literal pose. "
                    "Example: transcript 'My soldiers push forward' + visual 'man with mouth open in sky' -> "
                    "\"My soldiers push forward!\" — a man fiercely shouting his command.\n\n"
                    "When there is NO dialogue (transcript is empty, None, or [no speech]): "
                    "Output ONLY a descriptive visual/action caption. NEVER include 'no speech', '[no speech]', or similar. "
                    "Use the full narrative context (video title, previous scenes) to infer what the scene shows. "
                    "The visual caption from BLIP may be wrong for chaotic/action shots—use narrative logic to correct it.\n\n"
                    "Output one line per scene in order, no extra text."
                )
            prompt = f"{instructions}{cooking_block}\n\n{ctx}\nScenes:\n{joined}\n\nCaptions:"
            response = client.models.generate_content(model=model_name, contents=prompt)
            text = (getattr(response, "text", None) or "").strip()
            if not text:
                return None
            lines_out = [self._strip_scene_prefix(l.strip()) for l in text.splitlines() if l.strip()]
            while len(lines_out) < n:
                lines_out.append("")
            return lines_out[:n]
        except Exception as e:
            print(f"[Gemini] Final caption production failed: {e}")
            return None

    def _gemini_global_enhance_captions(
        self,
        scenes_data: List[Dict],
        video_context: Optional[Dict] = None,
    ) -> Optional[List[str]]:
        """
        Global understanding pass: correct transcripts, correct captions, optional web search,
        then produce final captions from full context.
        """
        if not self._gemini_api_key or not scenes_data:
            return None
        n = len(scenes_data)
        if n > self._gemini_hard_scene_cap:
            print(
                f"[Gemini] Global pass skipped: {n} scenes exceeds cap {self._gemini_hard_scene_cap}"
            )
            return None

        # Pass 1: correct transcripts
        corrected_transcripts = self._gemini_correct_transcripts_batch(scenes_data)
        if corrected_transcripts is None:
            corrected_transcripts = [
                (s.get("transcript") or "").strip() for s in scenes_data
            ]

        # Pass 2: correct captions
        corrected_captions = self._gemini_correct_captions_batch(scenes_data)
        if corrected_captions is None:
            corrected_captions = [
                self._deduplicate_repeated_words((s.get("caption") or "").strip())
                for s in scenes_data
            ]

        # Pass 3: optional web context (only if S2S_USE_WEB_CONTEXT enabled)
        web_context = None
        if self._use_web_context and video_context:
            vn = video_context.get("video_name", "").strip()
            vd = (video_context.get("description") or "").strip()
            if vn:
                web_context = self._fetch_context_from_web(vn, vd)

        # Pass 4: produce final captions
        return self._gemini_produce_final_captions(
            corrected_transcripts,
            corrected_captions,
            video_context=video_context,
            web_context=web_context,
        )

    def _gemini_analyze_story(
        self, scenes: List[Dict], video_context: Optional[Dict] = None
    ) -> Optional[Dict]:
        """
        Pass 1: Analyze which scenes have a meaningful visual or character change.
        Returns e.g. {"visual_change_indices": [1, 3, 4, 6]} (1-based), or None on failure.
        """
        if not self._gemini_api_key or not self._gemini_api_key.strip():
            return None
        if not scenes:
            return None
        try:
            from google import genai
        except ImportError:
            return None
        try:
            client = genai.Client(api_key=self._gemini_api_key)
            model_name = os.environ.get("GEMINI_MODEL", "gemini-2.0-flash")
            scene_descriptions = []
            for scene in scenes:
                num = scene.get("scene_number", len(scene_descriptions) + 1)
                visual = self._deduplicate_repeated_words((scene.get("caption") or "").strip())
                transcript = (scene.get("transcript") or "").strip()[:100]
                scene_descriptions.append(
                    f"Scene {num}: Visual: {visual or 'None'}. Transcript snippet: {transcript or 'None'}"
                )
            joined = "\n".join(scene_descriptions)
            prompt = (
                "Given these scenes (visual description + transcript snippet for each), "
                "which scene numbers have a meaningful visual or character change from the previous scene? "
                "Include scene 1 (the first scene always has a visual).\n\n"
                f"{joined}\n\n"
                "Output ONLY a JSON object, no other text. Example: {\"visual_change_indices\": [1, 3, 5]}"
            )
            response = client.models.generate_content(model=model_name, contents=prompt)
            text = (getattr(response, "text", None) or "").strip()
            if not text:
                return None
            # Extract JSON (handle markdown code blocks; array can have numbers and commas)
            json_match = re.search(
                r'\{\s*"visual_change_indices"\s*:\s*\[[^\]]*\]\s*\}',
                text,
            )
            if json_match:
                data = json.loads(json_match.group())
                indices = data.get("visual_change_indices", [])
                if isinstance(indices, list) and all(isinstance(i, int) for i in indices):
                    print(f"[Gemini] Story analysis: visual changes at scenes {indices}")
                    return {"visual_change_indices": indices}
            return None
        except Exception as e:
            print(f"Gemini story analysis failed: {e}")
            return None

    def _gemini_enhance_captions_batch(
        self,
        scenes: List[Dict],
        video_context: Optional[Dict] = None,
        visual_change_indices: Optional[List[int]] = None,
    ) -> Optional[List[str]]:
        """
        Use Gemini to enhance captions for scenes, splitting into batches if needed.

        For videos with many scenes, splits into batches and processes sequentially
        with delays to respect rate limits. Returns a list of caption strings matching
        the input scenes order, or None if Gemini is unavailable or fails.

        Args:
            scenes: List of scene dicts with caption and transcript.
            video_context: Optional dict with video_name and optionally description.
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

                context_block = ""
                if video_context:
                    video_name = video_context.get("video_name", "").strip()
                    video_desc = (video_context.get("description") or "").strip()
                    if video_name or video_desc:
                        context_block = "Video context (use this to create a coherent narrative):\n"
                        if video_name:
                            context_block += f"- Video title: {video_name}\n"
                        if video_desc:
                            context_block += f"- Description: {video_desc[:300]}\n"
                        context_block += "\n"

                selective_anchor_block = ""
                if visual_change_indices is not None:
                    selective_anchor_block = (
                        f"IMPORTANT: Scenes with visual/character changes (add a short visual anchor): {visual_change_indices}. "
                        "For all other scenes, output ONLY the quoted dialogue, no visual anchor after the quotes.\n"
                        "EXCEPTION: If the transcript is empty / None / [no speech], output ONLY a visual/action caption "
                        "(NO quotes), even if the scene is not in the visual-change list.\n"
                    )

                cooking_block = ""
                if video_context and self._is_cooking_video(video_context):
                    cooking_block = self._get_cooking_domain_instructions()

                if self._summarize_captions:
                    system_instructions = (
                        "You are a storyboard caption editor. Create concise captions that still read as a coherent story.\n\n"
                        "SUMMARIZE: Combine repetitive sentences and remove filler (side comments, jokes, meta-talk about the process, "
                        "and repeated exclamations) while keeping the key ideas and actions. "
                        "For cooking/baking, keep the main steps, important ingredients, key quantities, and critical temperature/timing; "
                        "you may merge multiple spoken sentences into 1–2 clear sentences per scene.\n\n"
                    "AVOID REPETITION: Do not repeat the same instruction in consecutive scenes. "
                    "If a step was already stated in the previous scene, make the next caption reflect progress, result, or a new detail.\n\n"
                        f"{selective_anchor_block}"
                        "Task:\n"
                        "- For every scene, output exactly ONE caption line.\n"
                        "- Format: \"<Dialogue>\" — <short visual anchor> when a visual anchor is needed; "
                        "otherwise just \"<Dialogue>\" with no anchor.\n"
                        "- Put the summarized spoken content first in quotes. The visual anchor (when used) should be brief "
                        "(a few words, e.g. \"whisking vigorously\", \"folding in chocolate chips\").\n"
                        "- Do NOT include 'Scene N:' or scene numbers.\n"
                        "- It is OK to drop filler chatter that does not change the meaning (e.g. jokes about being tired, "
                        "comments about using a stand mixer, or repeated 'wow' reactions).\n"
                        "- Use transitional phrasing where it helps (e.g., \"First…\", \"Then…\", "
                        "\"However…\", \"Finally…\") to connect scenes as a story.\n"
                        "- Maintain thematic continuity across scenes and a clear beginning-middle-end when the content supports it.\n"
                        "- Output one line per scene in order, no extra text before or after."
                    )
                else:
                    system_instructions = (
                        "You are a storyboard caption editor. Create captions that flow as a single "
                        "narrative, not isolated statements. For each scene, you will be given "
                        "a visual description and a rough transcript (may contain ASR errors).\n\n"
                        f"{selective_anchor_block}"
                        "Task:\n"
                        "- For every scene, output exactly ONE caption line.\n"
                        "- Format: \"<Dialogue>\" — <short visual anchor> when a visual anchor is needed; "
                        "otherwise just \"<Dialogue>\" with no anchor.\n"
                        "- Put the spoken content first in quotes. The visual anchor (when used) should be brief "
                        "(a few words, e.g. \"in a Minecraft setting\", \"at a fiery backdrop\").\n"
                        "- Do NOT include 'Scene N:' or scene numbers.\n"
                        "- CRITICAL: Preserve ALL original content. Do NOT condense or summarize. Include every idea, "
                        "example, and explanation from the transcript. Fix ASR errors and grammar only. "
                        "Original content cannot be missed. Long captions are fine.\n"
                        "- Use transitional phrasing where it helps (e.g., \"First…\", \"Then…\", "
                        "\"However…\", \"Ultimately…\") to connect scenes as a story.\n"
                        "- Maintain thematic continuity across scenes and a clear beginning-middle-end when the content supports it.\n"
                        "- Output one line per scene in order, no extra text before or after."
                    )
                if cooking_block:
                    system_instructions += cooking_block

                prompt = f"{system_instructions}\n\n{context_block}Scenes:\n{joined}\n\nCaptions:"

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
                    # Strip "Scene N:" prefix if model still outputs it.
                    cleaned = [self._strip_scene_prefix(c) for c in batch_result[:len(batch_scenes)]]
                    all_captions.extend(cleaned)

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
    
    def enhance_scene_captions(
        self, scenes_data: List[Dict], video_context: Optional[Dict] = None
    ) -> List[Dict]:
        """
        Enhance captions for all scenes in a video
        
        Args:
            scenes_data (List[Dict]): List of scene dictionaries with 'caption' and 'transcript' fields
            video_context (Optional[Dict]): Optional context with 'video_name' and 'description' for narrative flow
            
        Returns:
            List[Dict]: Updated scenes with enhanced captions
        """
        if not scenes_data:
            return []

        # Try Gemini enhancement first.
        gemini_captions: Optional[List[str]] = None
        if self._gemini_api_key and self._gemini_api_key.strip():
            if self._use_global_caption_pass:
                # Global understanding pass: correct transcripts, correct captions, optional web search, produce final captions.
                gemini_captions = self._gemini_global_enhance_captions(
                    scenes_data, video_context=video_context
                )
            if gemini_captions is None:
                # Fallback to batched enhancement
                story_analysis = self._gemini_analyze_story(scenes_data, video_context=video_context)
                visual_change_indices = (
                    story_analysis.get("visual_change_indices")
                    if story_analysis
                    else None
                )
                gemini_captions = self._gemini_enhance_captions_batch(
                    scenes_data,
                    video_context=video_context,
                    visual_change_indices=visual_change_indices,
                )

        enhanced_scenes: List[Dict] = []

        for idx, scene in enumerate(scenes_data):
            scene_number = scene.get("scene_number", idx + 1)
            visual_caption = scene.get("caption", "")
            transcript = scene.get("transcript", "")

            if gemini_captions is not None and idx < len(gemini_captions):
                candidate = gemini_captions[idx].strip()
                # Guard: Gemini can output empty quoted dialogue like "" — <anchor>
                # when transcript is empty but prompts prefer "quoted dialogue only".
                # In that case, fall back to rule-based visual caption.
                transcript_is_empty = not (transcript or "").strip()
                candidate_is_empty_quotes = bool(
                    transcript_is_empty
                    and candidate
                    and re.match(r'^"\s*"\s*([—\-]\s*.*)?$', candidate)
                )
                if candidate and not candidate_is_empty_quotes:
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