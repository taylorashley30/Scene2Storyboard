#!/usr/bin/env python3
"""
Lightweight evaluation script for Scene2Storyboard.

Features:
- Runs the existing backend pipeline for each video (via HTTP API).
- Measures total processing time per video.
- Computes video duration from the processed video file.
- Logs per-video metrics to a CSV file:
    video_name, video_duration_seconds, processing_time_seconds, scene_count
- Provides a helper to manually mark per-scene relevance (1/0) and
  compute scene relevance accuracy.
- Prints simple summary statistics across all runs.

Requirements:
- Backend server running at http://localhost:8000
  (see main.py; typically: `uvicorn main:app --reload` from backend directory).
"""

import csv
import os
import statistics
import time
from typing import Dict, List, Optional, Tuple

import cv2
import requests


API_BASE_URL = os.environ.get("S2S_API_BASE_URL", "http://localhost:8000")
DEFAULT_TIMEOUT_SECONDS = 900  # 15 minutes (Whisper + BLIP on CPU can be slow)


def get_video_duration_seconds(video_path: str) -> Optional[float]:
    """Return video duration in seconds using OpenCV, or None if unavailable."""
    if not video_path or not os.path.exists(video_path):
        print(f"[Eval] Video path not found for duration: {video_path}")
        return None

    cap = cv2.VideoCapture(video_path)
    try:
        fps = cap.get(cv2.CAP_PROP_FPS) or 0.0
        frame_count = cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0.0
    finally:
        cap.release()

    if fps <= 0 or frame_count <= 0:
        print(f"[Eval] Could not determine FPS/frame count for: {video_path}")
        return None

    return float(frame_count / fps)


def run_youtube_pipeline(
    youtube_url: str,
    video_name: Optional[str] = None,
    use_pyscenedetect: bool = True,
) -> Tuple[Optional[Dict], Optional[float]]:
    """
    Run the existing /process/youtube endpoint and measure total processing time.

    Returns:
        (result_json_dict, processing_time_seconds) or (None, None) on failure.
    """
    payload = {
        "youtube_url": youtube_url,
        "use_pyscenedetect": use_pyscenedetect,
        "video_name": video_name,
    }

    print(f"\n[Eval] Processing YouTube video: {youtube_url}")
    print(f"[Eval] POST {API_BASE_URL}/process/youtube")

    start_time = time.time()
    try:
        response = requests.post(
            f"{API_BASE_URL}/process/youtube",
            json=payload,
            timeout=DEFAULT_TIMEOUT_SECONDS,
        )
    except requests.exceptions.Timeout:
        print("[Eval] ❌ Request timed out.")
        return None, None
    except requests.exceptions.ConnectionError:
        print("[Eval] ❌ Could not connect to backend. Is it running?")
        return None, None
    except Exception as exc:
        print(f"[Eval] ❌ Unexpected error during request: {exc}")
        return None, None
    end_time = time.time()

    processing_time = end_time - start_time

    if response.status_code != 200:
        print(f"[Eval] ❌ Request failed with status {response.status_code}")
        print(f"[Eval] Response: {response.text}")
        return None, None

    result = response.json()
    print("[Eval] ✅ Video processed successfully.")
    print(f"[Eval] Total processing time: {processing_time:.2f} seconds")
    return result, processing_time


def extract_basic_metrics(
    pipeline_result: Dict,
    processing_time_seconds: float,
) -> Dict:
    """
    Extract core evaluation metrics from a pipeline result + timing.

    Returns dict with:
        video_name
        video_duration_seconds
        processing_time_seconds
        scene_count
        scenes (for optional relevance labeling)
    """
    scene_metadata = pipeline_result.get("scene_metadata", {}) or {}

    video_name = scene_metadata.get("video_name") or pipeline_result.get("video_name") or "unknown"
    scene_count = scene_metadata.get("total_scenes")
    if scene_count is None:
        scenes = scene_metadata.get("scenes") or []
        scene_count = len(scenes)
    else:
        scenes = scene_metadata.get("scenes") or []

    video_path = scene_metadata.get("video_path")
    video_duration_seconds = get_video_duration_seconds(video_path) if video_path else None

    if video_duration_seconds is None:
        print("[Eval] ⚠️ Video duration could not be determined; metrics will omit duration-based ratios.")

    metrics = {
        "video_name": video_name,
        "video_duration_seconds": video_duration_seconds,
        "processing_time_seconds": processing_time_seconds,
        "scene_count": scene_count,
        "scenes": scenes,
    }

    print(f"[Eval] Video: {video_name}")
    print(f"[Eval] Scene count: {scene_count}")
    if video_duration_seconds is not None:
        print(f"[Eval] Video duration: {video_duration_seconds:.2f} seconds")
        if video_duration_seconds > 0:
            pt_per_min = processing_time_seconds / (video_duration_seconds / 60.0)
            print(f"[Eval] Processing time per minute of video: {pt_per_min:.2f} sec/min")

    return metrics


def mark_scene_relevance(scenes: List[Dict]) -> Tuple[int, int, float]:
    """
    Interactive helper to manually mark each detected scene as relevant (1) or not (0).

    Returns:
        relevant_scenes (int)
        evaluated_scenes (int)
        accuracy (float in [0,1], or 0.0 if none evaluated)
    """
    if not scenes:
        print("[Eval] No scenes available for relevance labeling.")
        return 0, 0, 0.0

    print("\n[Eval] Manual Scene Relevance Labeling")
    print("--------------------------------------")
    print("For each scene, enter:")
    print("  1 = Relevant")
    print("  0 = Not relevant")
    print("  s = Skip this scene")
    print("  q = Quit labeling early\n")

    relevant_count = 0
    evaluated_count = 0

    for idx, scene in enumerate(scenes, start=1):
        scene_number = scene.get("scene_number", idx)
        start_time = scene.get("start_time")
        end_time = scene.get("end_time")
        caption = (scene.get("caption") or "").strip()

        print(f"\nScene {scene_number}")
        if start_time is not None and end_time is not None:
            duration = end_time - start_time
            print(f"  Time: {start_time:.2f}s – {end_time:.2f}s (duration {duration:.2f}s)")
        if caption:
            # Truncate long captions for readability
            display_caption = caption if len(caption) <= 220 else caption[:217] + "..."
            print(f"  Caption: {display_caption}")
        frame_path = scene.get("frame_path")
        if frame_path:
            print(f"  Frame: {frame_path}")

        while True:
            user_input = input("  Relevant? [1/0/s/q]: ").strip().lower()
            if user_input in {"1", "0", "s", "q", ""}:
                break
            print("  Please enter 1, 0, s, q, or press Enter to skip.")

        if user_input == "q":
            break
        if user_input in {"s", ""}:
            continue

        evaluated_count += 1
        if user_input == "1":
            relevant_count += 1

    accuracy = (relevant_count / evaluated_count) if evaluated_count > 0 else 0.0
    print(
        f"\n[Eval] Scene relevance: {relevant_count}/{evaluated_count} "
        f"({accuracy * 100:.1f}%) labeled as relevant."
    )
    return relevant_count, evaluated_count, accuracy


def write_metrics_csv(csv_path: str, rows: List[Dict]) -> None:
    """Write per-video metrics to CSV with fixed schema."""
    fieldnames = [
        "video_name",
        "video_duration_seconds",
        "processing_time_seconds",
        "scene_count",
    ]
    os.makedirs(os.path.dirname(csv_path), exist_ok=True)

    with open(csv_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    "video_name": row.get("video_name"),
                    "video_duration_seconds": (
                        f"{row['video_duration_seconds']:.3f}"
                        if row.get("video_duration_seconds") is not None
                        else ""
                    ),
                    "processing_time_seconds": f"{row['processing_time_seconds']:.3f}",
                    "scene_count": row.get("scene_count", 0),
                }
            )

    print(f"\n[Eval] Per-video metrics written to CSV: {csv_path}")


def print_summary(rows: List[Dict], relevance_accuracies: List[float]) -> None:
    """Print aggregate summary across all evaluated videos."""
    if not rows:
        print("[Eval] No successful runs to summarize.")
        return

    processing_times = [r["processing_time_seconds"] for r in rows]
    avg_processing_time = statistics.mean(processing_times)

    durations = [r["video_duration_seconds"] for r in rows if r.get("video_duration_seconds")]
    if durations:
        total_processing_time = sum(processing_times)
        total_video_minutes = sum(durations) / 60.0
        processing_time_per_minute = (
            total_processing_time / total_video_minutes if total_video_minutes > 0 else 0.0
        )
    else:
        processing_time_per_minute = None

    print("\n========== Evaluation Summary ==========")
    print(f"Videos evaluated: {len(rows)}")
    print(f"Average processing time: {avg_processing_time:.2f} seconds")
    if processing_time_per_minute is not None:
        print(
            "Processing time per minute of video "
            f"(aggregate): {processing_time_per_minute:.2f} sec/min"
        )
    else:
        print("Processing time per minute of video: N/A (missing duration data)")

    if relevance_accuracies:
        avg_accuracy = statistics.mean(relevance_accuracies)
        print(f"Average scene relevance accuracy: {avg_accuracy * 100:.1f}%")
    else:
        print("Average scene relevance accuracy: N/A (no relevance labels collected)")
    print("========================================\n")


def main() -> None:
    """
    Run evaluation over a small set of videos.

    Edit the VIDEOS_TO_TEST list below to customize which videos are evaluated.
    """
    # Example configuration: add or edit entries here for testing.
    # Each entry should at least contain a "youtube_url". "video_name" is optional.
    VIDEOS_TO_TEST: List[Dict[str, str]] = [
    # {
    #     "youtube_url": "https://youtu.be/M9iVHu6J7y8?si=dgI4xoT2KBan3i2m",
    #     "video_name": "vogue",
    # },
    # {
    #     "youtube_url": "https://youtube.com/shorts/4OooxUAgvjs?si=y2NBQPJMwiemSd9P",
    #     "video_name": "gnocchi",
    # },
    # {
    #     "youtube_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    #     "video_name": "rick roll",
    # },
    {
        "youtube_url": "https://youtube.com/shorts/Aphfzpf9zhI?si=2lbCwFSYdtrPMx-H",
        "video_name": "brownie",
    },
]

    if not VIDEOS_TO_TEST:
        print(
            "[Eval] No videos configured. Edit VIDEOS_TO_TEST in eval_metrics.py "
            "to add one or more YouTube URLs."
        )
        return

    all_rows: List[Dict] = []
    relevance_accuracies: List[float] = []

    for cfg in VIDEOS_TO_TEST:
        youtube_url = cfg.get("youtube_url")
        if not youtube_url:
            print("[Eval] Skipping entry without 'youtube_url' key.")
            continue

        video_name = cfg.get("video_name")

        result, processing_time = run_youtube_pipeline(
            youtube_url=youtube_url,
            video_name=video_name,
            use_pyscenedetect=True,
        )
        if not result or processing_time is None:
            continue

        metrics = extract_basic_metrics(result, processing_time_seconds=processing_time)

        # Optional interactive scene relevance labeling
        while True:
            label_input = input(
                "Label scene relevance for this video? [y/N]: "
            ).strip().lower()
            if label_input in {"y", "n", ""}:
                break
            print("Please enter 'y' or 'n' (or press Enter for 'n').")

        if label_input == "y":
            _, evaluated_count, accuracy = mark_scene_relevance(metrics.get("scenes") or [])
            if evaluated_count > 0:
                relevance_accuracies.append(accuracy)

        all_rows.append(metrics)

    # Write CSV with per-video metrics
    csv_path = os.path.join(os.path.dirname(__file__), "evaluation_metrics.csv")
    write_metrics_csv(csv_path, all_rows)

    # Print aggregate summary
    print_summary(all_rows, relevance_accuracies)


if __name__ == "__main__":
    main()

