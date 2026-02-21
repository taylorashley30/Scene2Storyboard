# Scene2Storyboard — Product Requirements Document (PRD)

**Version:** 1.1  
**Last updated:** February 20, 2026  
**Status:** Backend pipeline complete with Gemini enhancement working; frontend and caption quality improvements in focus.

---

## 1. Project overview

### 1.1 Purpose

Scene2Storyboard is a **multimodal AI application** that turns videos (local file or YouTube URL) into **comic-strip-style storyboards**. It uses:

- **Vision:** scene detection and key-frame extraction, image captioning (BLIP)
- **Audio:** speech-to-text (Whisper) per scene
- **Text:** caption enhancement (rule-based or optional OpenAI) and storyboard layout

Output: a single storyboard image (e.g. `storyboard.jpg`) with panels and captions, plus session metadata and frames for reuse.

### 1.2 Goals

- Accept video via **file upload** or **YouTube URL**
- Detect **scene boundaries** and extract one key frame per scene
- **Transcribe** speech per scene (Whisper)
- **Caption** each frame visually (BLIP)
- **Enhance** captions (fix ASR errors, format for comic style)
- **Generate** a comic-strip image (Pillow) and expose it via API
- (Planned) **Frontend** for upload, progress, and storyboard view/download

### 1.3 Tech stack

| Layer        | Technology |
|-------------|------------|
| Backend     | Python 3, FastAPI, uvicorn |
| Video/Audio | OpenCV, PySceneDetect, MoviePy, yt-dlp |
| AI          | OpenAI Whisper, BLIP (Hugging Face), Gemini API (google-genai) |
| Image       | Pillow (PIL) |
| Frontend    | React, TypeScript, Vite (scaffold only so far) |

---

## 2. What has been done (from code and structure)

### 2.1 Implemented and wired

1. **Project setup**  
   Backend (FastAPI, venv, `requirements.txt`), frontend (React + Vite + TS), `.gitignore`, basic docs.

2. **Video input**  
   - **Upload:** `POST /process/upload` — multipart file, validation, temp save then move to session folder.  
   - **YouTube / Instagram:** `POST /process/youtube` — URL validation (YouTube or Instagram), yt-dlp download to temp, then move to session folder.

3. **Scene detection**  
   PySceneDetect `ContentDetector` with configurable sensitivity (`S2S_SCENE_THRESHOLD`, default 30.0) and minimum scene duration filter (`S2S_MIN_SCENE_DURATION`, default 1.5s). Scenes shorter than the minimum are merged with the previous scene to reduce repetition from quick visual cuts that don't align with dialogue. One key frame per scene saved under session `snippets/`; scene list with `start_time`, `end_time`, `frame_path`, `frame_filename`.

4. **Audio transcription**  
   MoviePy audio extraction (mono 16 kHz WAV); Whisper (configurable via `S2S_WHISPER_MODEL_SIZE`, default `base` for speed) full-file transcribe; segments mapped to scenes using segment start time and midpoint (not just overlap) to avoid assigning the same dialogue to multiple scenes; per-scene transcript string (with internal cleaning in `audio_transcriber`).

5. **Image captioning**  
   BLIP (Salesforce/blip-image-captioning-base) via Hugging Face; lazy load; GPU/CPU; one caption per scene frame; stored in scene `caption`.

6. **Caption enhancement**  
   - **Rule-based:** clean transcript (hardcoded fixes), combine visual + dialogue (`Visual — "Dialogue"`), truncate long dialogue at 80 chars. Used as fallback when Gemini is unavailable or fails.  
   - **Gemini enhancement (preferred):** When `GEMINI_API_KEY` is set, uses **Gemini API (`google-genai` package)** with batching support for videos with many scenes. Splits scenes into batches (default 30 per request), processes sequentially with delays to respect rate limits. Fixes ASR errors (e.g., "fuel pp" → "fuel pump", "pow" → "power", "Toe" → "tow"), corrects grammar, and formats captions. Falls back to rule-based on timeout, rate limits, or errors.  
   Output stored in scene `enhanced_caption`; storyboard uses `enhanced_caption`.

7. **Storyboard generation**  
   Pillow grid (3–4 columns), panel = resized frame + caption area; title “Storyboard - N Scenes”; borders; text wrap; saved as `storyboard.jpg` in session folder.

8. **API surface**  
   - `GET /health`  
   - `POST /process/upload`, `POST /process/youtube`  
   - `GET /sessions`  
   - `GET /scenes/{session_id}` (metadata)  
   - `POST /generate-storyboard/{session_id}`  
   - `GET /storyboard/{session_id}` (image)  
   - `GET /frame/{session_id}/{frame_filename}` (single frame from `snippets/`)

9. **Persistence**  
   Per-session folder under `backend/scenes/{session_id}/`: video, WAV (if extracted), `snippets/*.jpg`, `metadata.json`, `storyboard.jpg`.

### 2.2 Not done / partial

- **Frontend:** Still default Vite+React template; no upload UI, no YouTube input, no progress, no storyboard display or download.
- **Local LLM:** Scene2Storyboard.txt describes Mistral/TinyLlama for caption enhancement; not implemented (only Gemini API or rule-based).
- **Progress reporting:** Processing is synchronous; no SSE/WebSocket or polling for step-by-step progress.
- **YouTube Shorts support:** URL validation accepts `youtube.com/shorts/` URLs; full pipeline tested and working.
- **Instagram support:** URL validation accepts Instagram posts (`/p/`), reels (`/reel/`, `/reels/`), and TV (`/tv/`). Download via yt-dlp; some posts may require cookies if Instagram blocks unauthenticated access.

---

## 3. Current phase: final captions — problems

This section describes **issues and limitations of the current “final captions” phase** (BLIP + transcript → enhanced caption → storyboard).

### 3.1 Transcript errors in final captions

- **Observed:** Final `enhanced_caption` can still contain clear ASR errors (e.g. “he we are”, “the’se”) even when rule-based fixes exist for them.
- **Causes:**  
  - Rule-based path: `_clean_transcript` in `caption_enhancer` has a **small hardcoded list**; many mishearings are never corrected.  
  - LLM path: Model may not fix all errors or may introduce small changes; output is single-line and not validated against a lexicon.
- **Impact:** Storyboard panels show visibly wrong text, which hurts perceived quality.

### 3.2 Rule-based enhancement limitations

- **Hardcoded replacements:** `caption_enhancer._clean_transcript` and `audio_transcriber._clean_transcript` use fixed dicts; not scalable and duplicated across two modules.
- **Truncation:** Dialogue is cut at 80 characters on a word boundary; can cut mid-sentence and leave “...” with no guarantee of grammatical closure.
- **No style control:** No “comic” or “punchy” shaping; format is effectively “Visual — ‘Dialogue’”.
- **No dialogue vs narration:** Every scene gets the same pattern; no distinction between spoken dialogue and narrator/text overlay.

### 3.3 LLM enhancement (Gemini) — current status and limitations

- **Gemini (working, free/paid tier):** When `GEMINI_API_KEY` is set, the backend uses **Gemini API (`google-genai` package, default model `gemini-2.0-flash`)** with **batching support** for videos with many scenes. For videos exceeding `GEMINI_MAX_SCENES_PER_REQUEST` (default 30), scenes are split into batches and processed sequentially with delays (`GEMINI_BATCH_DELAY`, default 2s) to respect rate limits. Falls back to rule-based on timeout (90s), rate limits, or errors.\n- **No OpenAI usage:** All OpenAI-based enhancement has been removed/disabled; setting `OPENAI_API_KEY` has no effect, so we never hit paid OpenAI endpoints.\n- **Comparison results (tested Feb 2026):** Side-by-side comparison of rule-based vs Gemini-enhanced captions for a 32-scene YouTube Shorts video shows Gemini **significantly improves accuracy**: fixes ASR errors like "fuel pp" → "fuel pump", "pow" → "power", "Toe" → "tow", "starts" → "starter", "matt, h" → "matter", "Anoth day" → "Another day", "work" → "working", "he" → "here". Rule-based captions retain these errors and truncate dialogue at 80 chars, leading to repetitive and inaccurate storyboards.\n- **Remaining limitations:** Single-line constraint (captions designed as single lines, may wrap visually); no post-spellcheck validation layer; Scene 32 anomaly (black-and-white photo) appears in both rule-based and Gemini outputs, suggesting a scene detection or frame extraction issue rather than a caption problem.

### 3.4 Integration and data flow

- **Two sources of “cleaning”:** Transcript is cleaned in both `audio_transcriber._clean_transcript` (before it’s stored in scene) and in `caption_enhancer._clean_transcript` (when building caption). Logic and replacement sets can drift.
- **Caption key usage:** Storyboard generator correctly uses `enhanced_caption`; metadata keeps both `caption` (BLIP) and `enhanced_caption`. Downstream code must consistently use `enhanced_caption` for display.

### 3.5 Storyboard presentation

- **Fixed caption height:** 90px per panel can be too much for one line or too little for wrapped multi-line; not responsive to content length.
- **Font:** System font (e.g. Arial on macOS); no project-bundled font, so layout can differ across environments.
- **No accessibility:** No alt text or structured caption export for screen readers.

### 3.6 Real-world comparison: Rule-based vs Gemini-enhanced (tested Feb 2026)

**Test case:** 32-scene YouTube Shorts video (car troubleshooting theme, ~55 seconds).

**Rule-based captions (session `20260220_070947`):**
- **ASR errors retained:** "fuel pp" (should be "fuel pump"), "pow" (should be "power"), "Toe" (should be "tow"), "starts" (should be "starter"), "matt, h" (should be "matter"), "Anoth day, anoth fail" (should be "Another day, another fail"), "work" (should be "working"), "he" (should be "here").
- **Truncation:** Dialogue cut at 80 characters mid-sentence (e.g., Scene 7: "...Well, it's not...", Scene 26: "...she's going..."), leading to incomplete thoughts.
- **Repetitive:** Many consecutive scenes show nearly identical captions (e.g., Scenes 1-4 all repeat "put the car in rice, try spanking it").
- **Result:** Storyboard feels inaccurate and repetitive; technical terms are wrong, making it less credible.

**Gemini-enhanced captions (session `20260220_071838`):**
- **ASR errors corrected:** "fuel pump" (corrected from "fuel pp"), "power" (from "pow"), "tow" (from "Toe"), "starter" (from "starts"), "matter" (from "matt, h"), "Another day, another fail" (from "Anoth day, anoth fail"), "working" (from "work"), "here" (from "he").
- **Complete dialogue:** No truncation; full sentences preserved (e.g., Scene 7: full "fuel pump" explanation, Scene 26: complete towing plan).
- **Varied:** Each scene has distinct caption even when visuals are similar, reducing repetition.
- **Result:** Storyboard is more accurate, readable, and professional; technical terms are correct.

**Conclusion:** Gemini enhancement provides **significant quality improvement** for storyboard captions, especially for videos with technical content or many scenes. The batching implementation (tested with 32 scenes) successfully processes longer videos while respecting rate limits.

**Known issue:** Scene 32 anomaly (black-and-white photo of a man in a suit) appears in both outputs, suggesting a scene detection or frame extraction issue at video end, not a caption problem.

### 3.7 Scene detection optimization (reducing repetition)

**Problem observed:** For videos with quick visual cuts (e.g., YouTube Shorts), PySceneDetect detects many short scenes (0.8–1s) that don't align with dialogue boundaries. This causes:
- **Repetitive captions:** The same dialogue appears in multiple consecutive scenes (e.g., Scenes 1–4 all repeat "put the car in rice, try spanking it").
- **Transcript misalignment:** Whisper segments that span multiple short scenes get assigned to all of them.

**Solutions implemented:**

1. **Minimum scene duration filter** (`S2S_MIN_SCENE_DURATION`, default 1.5s): Scenes shorter than this are merged with the previous scene. This reduces repetition from quick camera cuts while preserving major scene changes.
   - **Trade-off:** Very short but meaningful visual transitions (e.g., quick reaction shots) may be merged. For most videos, merging scenes < 1.5s improves caption quality without losing important content.

2. **Configurable detection threshold** (`S2S_SCENE_THRESHOLD`, default 30.0): Higher threshold = less sensitive = fewer cuts detected. Useful for videos with many quick cuts where you want fewer, longer scenes.
   - **Trade-off:** Increasing threshold too high (e.g., 50+) may miss legitimate scene changes in slower-paced videos.

3. **Improved transcript mapping:** Segments are assigned to scenes based on where they **start** or their **midpoint**, not just overlap. This prevents a single dialogue segment from appearing in multiple scenes.
   - **Example:** A segment spanning 0–3.5s will be assigned to Scene 1 (0–3.23s) only, not to Scenes 2 and 3 that occur during that segment.

**Recommendation:** For videos with many quick cuts (like YouTube Shorts), keep defaults (`S2S_MIN_SCENE_DURATION=1.5`, `S2S_SCENE_THRESHOLD=30.0`). For slower-paced videos or when you want more granular scene detection, reduce `S2S_MIN_SCENE_DURATION` to 0.8–1.0s or lower `S2S_SCENE_THRESHOLD` to 20–25.

---

## 4. Next phase (recommended)

### 4.1 Immediate next: frontend (Step 8)

- **Upload/YouTube UI:** File drop + YouTube URL input; validate and call `POST /process/upload` or `POST /process/youtube`.
- **Progress:** At least “Processing…” with optional polling of `GET /sessions` or a new status endpoint to show “ready” and link to storyboard.
- **Storyboard display:** Fetch `GET /storyboard/{session_id}` and show image; “Download” for `storyboard.jpg`.
- **Session list:** Use `GET /sessions` to show past runs and open a session’s storyboard.

### 4.2 Caption quality (in parallel or after frontend)

- **Unify transcript cleaning:** Single place (e.g. `caption_enhancer` or shared util) for transcript normalization and replacement list; have transcriber optionally use it so scene transcript is already clean.\n- **Gemini-first enhancement:** Prefer Gemini batch enhancement (free tier) via `GEMINI_API_KEY`, conservative scene caps (`GEMINI_MAX_SCENES_PER_REQUEST`, `GEMINI_HARD_SCENE_CAP`) and immediate fallback on any rate-limit or quota issues.\n- **No paid APIs by default:** OpenAI enhancement has been removed to guarantee no paid endpoint usage; a future local LLM path (e.g. Mistral/TinyLlama as in Scene2Storyboard.txt) can provide an offline option.\n- **Caption length/style:** Configurable max length; optional “comic style” prompt or post-process to keep captions short and punchy.\n- **Validation:** Optional spell-check or known-error pass on `enhanced_caption` before saving.

### 4.3 Later

- **Progress API:** Server-sent events or WebSocket for scene-by-scene progress.
- **Templates:** Multiple storyboard layouts (columns, strip, etc.).
- **Export:** PDF or structured (e.g. JSON) export of panels + captions for accessibility.

### 4.4 Running the backend and stopping it

- **`.env` is loaded automatically** when the app starts (from `backend/.env`), so `GEMINI_API_KEY` and `S2S_WHISPER_MODEL_SIZE` take effect without exporting in the shell.
- **Why Ctrl+C doesn’t stop everything immediately:** With `uvicorn main:app --reload`, there are two processes: a *reloader* (parent) and a *server* (child). The pipeline (Whisper, BLIP, etc.) runs in the server process and is **synchronous** and **long-running**. When you press Ctrl+C, the reloader may exit first; the child can keep running until it finishes the current request or is killed. Whisper/BLIP also don’t check for interrupts often, so the process can look “still running” for a while.
- **How to stop cleanly:** Press **Ctrl+C once** and wait a few seconds. If the server is in the middle of transcription or captioning, it may complete that request and then exit. If it doesn’t exit, press **Ctrl+C again** (or close the terminal). For long pipeline runs, consider starting without `--reload` so there’s only one process: `python -m uvicorn main:app --host 0.0.0.0 --port 8000`.

---

## 5. File inventory and responsibilities

### 5.1 Repository root

| File / folder       | Purpose |
|---------------------|--------|
| `README.md`         | Setup, usage, optional LLM (OpenAI), license. |
| `PROJECT_STRUCTURE.md` | Directory layout and high-level status. |
| `PROJECT_PROGRESS_SUMMARY.md` | Detailed progress, stack, achievements, next steps. |
| `PRODUCT_REQUIREMENTS_DOCUMENT.md` | This document. |
| `Scene2Storyboard.txt` | Implementation guide (video input, scene detection, Whisper, BLIP, LLM enhancement, storyboard, frontend). |
| `frontend/`         | React + TypeScript + Vite app (see below). |
| `backend/`          | FastAPI app and all processing (see below). |

### 5.2 Backend (`backend/`)

| File / folder       | Purpose |
|---------------------|--------|
| `main.py`           | FastAPI app, CORS, routes: health, upload, youtube, sessions, scenes, storyboard, frame. Orchestrates: file/YouTube → scene_detector → audio_transcriber → image_captioner → caption_enhancer → storyboard_generator; writes metadata. |
| `requirements.txt`  | Python dependencies (FastAPI, OpenCV, Whisper, BLIP, PySceneDetect, MoviePy, yt-dlp, Pillow, etc.). |
| `.env.example`      | Example env (e.g. `OPENAI_API_KEY`) for optional LLM. |
| `uploads/`          | Temp directory for uploaded or downloaded videos before move to session folder (often empty). |
| `scenes/`           | One folder per run: `{session_id}/` containing video, WAV (if any), `snippets/*.jpg`, `metadata.json`, `storyboard.jpg`. |
| `utils/__init__.py` | Makes `utils` a package. |
| `utils/file_handler.py` | Validates video extension; saves upload to `uploads/` with UUID name; cleanup helper. |
| `utils/youtube_handler.py` | Validates YouTube or Instagram URL; downloads via yt-dlp to `uploads/`; optional `get_video_info`. |
| `utils/scene_detector.py` | Creates session folder and `snippets/`; runs PySceneDetect ContentDetector; saves one frame per scene; builds scene list (times, paths); `save_metadata` writes `metadata.json`. |
| `utils/frame_extractor.py` | Frame/metadata extraction utilities (used or available for alternative extraction). |
| `utils/audio_transcriber.py` | Extracts audio (MoviePy) to WAV; loads Whisper; transcribes; maps segments to scene timestamps; `_clean_transcript` with hardcoded fixes; returns list of per-scene transcript strings. |
| `utils/image_captioner.py` | Loads BLIP processor/model (lazy); `caption_image(path)` returns one caption string; GPU/CPU. |
| `utils/caption_enhancer.py` | `_clean_transcript` (own fix list); `_create_storyboard_caption` (visual + transcript, truncate 80); optional **Gemini batch enhancement** via `GEMINI_API_KEY` with conservative scene caps to stay within free-tier rate limits; optional OpenAI enhancement via `OPENAI_API_KEY`; `enhance_caption` chooses backend in order Gemini → OpenAI → rule-based; `enhance_scene_captions(scenes)` adds `enhanced_caption` to each scene. |
| `utils/storyboard_generator.py` | Layout (cols/rows, panel size), `_create_panel` (frame + caption area), `_wrap_text`, `_load_font`; `generate_storyboard(scenes, output_path)` uses `frame_path` and `enhanced_caption`; `generate_storyboard_from_session(session_path)` loads metadata and calls `generate_storyboard`. |
| `test_full_pipeline.py` | Script to hit `/process/youtube`, check response and `GET /storyboard/{session_id}`. |
| `test_storyboard.py`   | Tests storyboard generation (layout, panels). |

### 5.3 Frontend (`frontend/`)

| File / folder       | Purpose |
|---------------------|--------|
| `index.html`        | Entry HTML. |
| `package.json`      | Dependencies and scripts (e.g. `npm run dev`). |
| `vite.config.ts`    | Vite config (dev server, build). |
| `tsconfig*.json`    | TypeScript config. |
| `src/main.tsx`      | React root mount. |
| `src/App.tsx`       | Root component (currently default Vite template; no Scene2Storyboard UI). |
| `src/App.css`       | Styles for default template. |
| `public/`           | Static assets. |

---

## 6. How files and components connect

### 6.1 Processing pipeline (backend)

```
User request (file or YouTube URL)
    ↓
main.py (route)
    ↓
file_handler (validate, save) OR youtube_handler (download) → temp video path
    ↓
scene_detector.process_video(video_path, video_name)
    → creates session folder + snippets/
    → writes initial metadata.json (no transcript/caption yet)
    → returns scene_metadata (session_path, scenes with frame_path, etc.)
    ↓
main: move video to session_path; set scene_metadata["video_path"]
    ↓
audio_transcriber.get_scene_transcripts(video_path, scene_timestamps)
    → extract WAV if needed, Whisper transcribe, map segments to scenes
    → returns list of transcript strings
    ↓
main: for each scene, set scene["transcript"]; image_captioner.caption_image(scene["frame_path"]) → scene["caption"]
    ↓
caption_enhancer.enhance_scene_captions(scene_metadata["scenes"])
    → each scene gets enhanced_caption (LLM or rule-based)
    ↓
storyboard_generator.generate_storyboard(scenes, session_path/storyboard.jpg)
    → reads frame_path, enhanced_caption per scene; builds image
    ↓
scene_detector.save_metadata(scene_metadata, session_path)
    ↓
Response: session_path, scene_metadata (incl. storyboard_path)
```

### 6.2 Data flow per scene

- **Inputs:** `frame_path` (from scene_detector), `transcript` (from audio_transcriber), `caption` (from image_captioner).
- **Enhancement:** caption_enhancer produces `enhanced_caption` (and keeps existing keys).
- **Output:** metadata.json holds `caption`, `transcript`, `enhanced_caption`; storyboard image uses only `frame_path` and `enhanced_caption`.

### 6.3 API → frontend (intended)

- **Upload/YouTube:** Frontend will POST to ` /process/upload` or `/process/youtube`, then use returned `session_path` (or session_id) to:
  - Poll or fetch `GET /sessions` or a dedicated status until “ready”
  - Load storyboard via `GET /storyboard/{session_id}`
- **History:** `GET /sessions` → list of session_id, video_name, total_scenes, has_storyboard; frontend can link to `/storyboard/{session_id}` or a detail view using `GET /scenes/{session_id}`.
- **Frames:** `GET /frame/{session_id}/{frame_filename}` serves files from `scenes/{session_id}/snippets/`.

### 6.4 Session folder layout (on disk)

```
backend/scenes/{session_id}/
├── {video_filename}.mp4      # or downloaded filename
├── {video_stem}.wav          # if audio extracted
├── snippets/
│   ├── scene_001.jpg
│   ├── scene_002.jpg
│   └── ...
├── metadata.json              # video_path, video_name, total_scenes, scenes[], storyboard_path, etc.
└── storyboard.jpg
```

`metadata.json` → used by `GET /scenes/{session_id}`, `generate_storyboard_from_session`, and any future frontend that shows scene list or regenerates storyboard.

---

## 7. Summary

- **Done:** End-to-end backend: upload/YouTube → scene detection → transcription → BLIP captions → caption enhancement → storyboard image and metadata; full API for sessions, scenes, storyboard, and frames.
- **Current phase issues:** Final captions still show ASR errors; rule-based enhancement is limited and duplicated; LLM path is optional and not always consistent; no local LLM; storyboard caption area and fonts are fixed.
- **Next phase:** Implement frontend (upload, YouTube, progress, storyboard view/download, session list); then improve caption quality (unified cleaning, optional local LLM, length/style control).

This PRD is the single place for project goals, current behavior, known problems, next steps, and how each file and component fits into the system.
