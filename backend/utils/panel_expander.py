#!/usr/bin/env python3
"""
Panel expansion: split long captions into multiple panels to avoid overflow.
When a scene's enhanced_caption exceeds max_caption_chars, split on sentence boundaries
and create multiple panels. When panels share a scene, assign_distinct_frames_to_panels
extracts multiple frames at evenly spaced timestamps instead of reusing the same frame.
"""

import os
import re
from collections import defaultdict
from typing import List, Dict, Optional


def assign_distinct_frames_to_panels(
    panels_data: List[Dict],
    video_path: str,
    session_path: str,
) -> List[Dict]:
    """
    When multiple panels share the same scene (same frame_path), extract distinct
    frames at evenly spaced timestamps within the scene's time range and assign
    one frame per panel.

    Args:
        panels_data: List of panel dicts with frame_path, frame_filename, scene_number,
                     start_time, end_time (from scene).
        video_path: Path to the video file.
        session_path: Path to the session folder (snippets/ is under this).

    Returns:
        Updated panels with distinct frame_path and frame_filename where applicable.
    """
    if not panels_data or not video_path or not session_path:
        return panels_data
    if not os.path.exists(video_path):
        return panels_data

    try:
        from utils.frame_extractor import FrameExtractor
    except ImportError:
        return panels_data

    extractor = FrameExtractor()
    snippets_dir = os.path.join(session_path, "snippets")
    os.makedirs(snippets_dir, exist_ok=True)

    # Group panels by (scene_number, frame_path) - panels that share a scene
    groups: Dict[tuple, List[int]] = defaultdict(list)
    for idx, panel in enumerate(panels_data):
        key = (panel.get("scene_number"), panel.get("frame_path", ""))
        groups[key].append(idx)

    for (scene_number, orig_frame_path), indices in groups.items():
        if len(indices) <= 1:
            continue
        # Need to extract N distinct frames for these panels
        panel = panels_data[indices[0]]
        start_time = panel.get("start_time", 0.0)
        end_time = panel.get("end_time", start_time + 1.0)
        duration = max(0.1, end_time - start_time)
        n = len(indices)

        # Evenly spaced timestamps within the scene
        timestamps = []
        for i in range(n):
            t = start_time + (duration * i) / max(1, n - 1)
            timestamps.append(min(max(t, start_time), end_time - 0.01))

        base_name = os.path.splitext(os.path.basename(orig_frame_path or "scene_001.jpg"))[0]
        for i, panel_idx in enumerate(indices):
            t = timestamps[i]
            frame_filename = f"{base_name}_panel_{i + 1}.jpg"
            frame_path = os.path.join(snippets_dir, frame_filename)
            try:
                frame = extractor.extract_frame_at_time(video_path, t)
                if extractor.save_frame(frame, frame_path):
                    panels_data[panel_idx]["frame_path"] = frame_path
                    panels_data[panel_idx]["frame_filename"] = frame_filename
            except Exception as e:
                print(f"[assign_distinct_frames] Failed to extract frame at {t}s: {e}")

    return panels_data


def expand_scenes_to_panels(
    scenes_data: List[Dict], max_caption_chars: int = 180
) -> List[Dict]:
    """
    Expand scenes into panels. Scenes with captions exceeding max_caption_chars
    are split into multiple panels, each reusing the same frame.

    Args:
        scenes_data: List of scene dicts with frame_path, enhanced_caption, etc.
        max_caption_chars: Max chars per caption before splitting.

    Returns:
        List of panel dicts with frame_path, enhanced_caption, and other keys
        needed by the storyboard generator.
    """
    panels: List[Dict] = []
    for scene in scenes_data:
        caption = (scene.get("enhanced_caption") or "").strip()
        frame_path = scene.get("frame_path", "")
        frame_filename = scene.get("frame_filename", "")
        scene_number = scene.get("scene_number", len(panels) + 1)

        if len(caption) <= max_caption_chars:
            panel = scene.copy()
            panel["enhanced_caption"] = caption
            panels.append(panel)
            continue

        # Split caption into chunks on sentence boundaries
        chunks = _split_caption_into_chunks(caption, max_caption_chars)
        for i, chunk in enumerate(chunks):
            panel = scene.copy()
            panel["enhanced_caption"] = chunk.strip()
            panel["frame_path"] = frame_path
            panel["frame_filename"] = frame_filename
            panel["scene_number"] = scene_number
            if len(chunks) > 1:
                panel["panel_index"] = i + 1
            panels.append(panel)
    return panels


def _split_into_sentences(text: str) -> List[str]:
    """
    Split text into sentences on . ! ? boundaries.
    Preserves the punctuation with each sentence.
    """
    if not text or not text.strip():
        return []
    # Split on sentence-ending punctuation followed by space or end
    parts = re.split(r'(?<=[.!?])\s+', text)
    return [p.strip() for p in parts if p.strip()]


def _normalize_for_dedup(s: str) -> str:
    """Normalize text for duplicate comparison: lowercase, collapse whitespace."""
    if not s:
        return ""
    # Strip trailing visual anchor after an em dash so that:
    #   "Sentence text.\" — in a kitchen"
    # and
    #   "Sentence text.\""
    # are treated as the same for dedup purposes.
    base = s
    # Split once on common dash patterns used before anchors.
    parts = re.split(r"\s+[–—-]\s+", base, maxsplit=1)
    if parts:
        base = parts[0]
    # Remove leading/trailing quotes which can vary slightly.
    base = base.strip().strip('"\''"“”‘’")
    # Lowercase and collapse whitespace.
    return re.sub(r"\s+", " ", base.lower().strip())


def deduplicate_panel_captions(panels_data: List[Dict]) -> List[Dict]:
    """
    Remove full-sentence repetition across panels. Tracks used sentences; if a
    caption (or full sentence) appeared in a previous panel, it is removed from
    later panels. Allows short continuity phrases (a few words) but not whole
    sentences or more.
    """
    if not panels_data:
        return panels_data

    used_sentences: set = set()
    result: List[Dict] = []

    for panel in panels_data:
        panel = panel.copy()
        caption = (panel.get("enhanced_caption") or "").strip()
        if not caption:
            result.append(panel)
            continue

        sentences = _split_into_sentences(caption)
        new_sentences: List[str] = []
        for s in sentences:
            norm = _normalize_for_dedup(s)
            if not norm or len(norm) < 10:  # Skip very short fragments (allow continuity)
                new_sentences.append(s)
                continue
            # Remove if exact match (whole sentence repeated)
            if norm in used_sentences:
                continue
            # Remove if this sentence is fully contained in a previously used one
            if any(norm in used for used in used_sentences if len(used) > len(norm)):
                continue
            new_sentences.append(s)
            used_sentences.add(norm)

        if new_sentences:
            panel["enhanced_caption"] = " ".join(new_sentences)
        else:
            # Continuity fragment: first ~6 words of original with ellipsis
            words = caption.split()[:6]
            panel["enhanced_caption"] = " ".join(words) + ("…" if len(words) >= 3 else "…")

        result.append(panel)

    return result


def _split_caption_into_chunks(text: str, max_chars: int) -> List[str]:
    """
    Split text into chunks based on the overall caption length.
    Aim for N reasonably balanced chunks instead of cutting strictly at max_chars.
    """
    if len(text) <= max_chars:
        return [text]

    # 1) Keep your existing anchor handling (" — visual anchor") the same
    dialogue_part = text
    anchor_part = ""
    anchor_match = re.search(r'\s+—\s+(.+)$', text)
    if anchor_match:
        anchor_part = " — " + anchor_match.group(1).strip()
        dialogue_part = text[: anchor_match.start()].strip()
        # If everything fits, return as-is
        if len(dialogue_part) + len(anchor_part) <= max_chars:
            return [text]

    # 2) Split the dialogue into sentences
    sentences = _split_into_sentences(dialogue_part)
    if not sentences:
        # fallback: your existing clause/length logic
        ...

    total_chars = sum(len(s) for s in sentences)

    # 3) Decide how many chunks we *actually* want
    #    (e.g., caption of 350 chars with max_chars=180 → 2 chunks)
    ideal_chunks = max(1, round(total_chars / max_chars))
    target_per_chunk = max_chars if ideal_chunks == 1 else total_chars / ideal_chunks

    # 4) Build chunks by accumulating sentences up to ~target_per_chunk
    chunks: List[str] = []
    current: List[str] = []
    current_len = 0

    for s in sentences:
        extra = (1 if current else 0) + len(s)  # space + sentence
        if current and current_len + extra > target_per_chunk * 1.2:
            # close current chunk if we are significantly over target
            chunks.append(" ".join(current))
            current = [s]
            current_len = len(s)
        else:
            current.append(s)
            current_len += extra

    if current:
        chunks.append(" ".join(current))

    # 5) Fix tiny tail chunks: merge very short final chunk back
    MIN_TAIL_CHARS = 30
    if len(chunks) >= 2 and len(chunks[-1]) < MIN_TAIL_CHARS:
        chunks[-2] = chunks[-2].rstrip() + " " + chunks[-1].lstrip()
        chunks.pop()

    # 6) Re‑attach anchor to the last chunk, never as its own panel
    if chunks and anchor_part:
        chunks[-1] = chunks[-1] + anchor_part

    return chunks
    