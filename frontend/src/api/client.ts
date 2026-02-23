/**
 * API client for Scene2Storyboard backend.
 * Uses /api proxy in dev (Vite rewrites to backend at localhost:8000).
 */
const API_BASE = import.meta.env.VITE_API_BASE ?? '/api';

export function apiUrl(path: string): string {
  const base = API_BASE.replace(/\/$/, '');
  const p = path.startsWith('/') ? path : `/${path}`;
  return `${base}${p}`;
}

export async function processYoutube(url: string): Promise<{ session_path: string; scene_metadata: unknown }> {
  const res = await fetch(apiUrl('/process/youtube'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ youtube_url: url }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error((err as { detail?: string }).detail ?? res.statusText);
  }
  return res.json();
}

export async function processUpload(file: File): Promise<{ session_path: string; scene_metadata: unknown }> {
  const form = new FormData();
  form.append('file', file);
  const res = await fetch(apiUrl('/process/upload'), {
    method: 'POST',
    body: form,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error((err as { detail?: string }).detail ?? res.statusText);
  }
  return res.json();
}

export interface SessionInfo {
  session_id: string;
  video_name: string;
  total_scenes: number;
  total_panels?: number;
  processing_timestamp: string;
  session_path: string;
  has_storyboard: boolean;
}

export async function deleteSession(sessionId: string): Promise<void> {
  const res = await fetch(apiUrl(`/sessions/${sessionId}`), { method: 'DELETE' });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error((err as { detail?: string }).detail ?? 'Failed to delete');
  }
}

export async function listSessions(): Promise<SessionInfo[]> {
  const res = await fetch(apiUrl('/sessions'));
  if (!res.ok) throw new Error('Failed to fetch sessions');
  const data = await res.json();
  const sessions = (data.sessions ?? []) as SessionInfo[];
  return sessions.filter((s) => s.has_storyboard);
}

export async function getScenes(sessionId: string): Promise<SceneMetadata> {
  const res = await fetch(apiUrl(`/scenes/${sessionId}`));
  if (!res.ok) throw new Error('Session not found');
  return res.json();
}

export function frameUrl(sessionId: string, frameFilename: string): string {
  return apiUrl(`/frame/${sessionId}/${frameFilename}`);
}

export function storyboardUrl(sessionId: string, page?: number): string {
  const base = apiUrl(`/storyboard/${sessionId}`);
  return page != null && page >= 1 ? `${base}?page=${page}` : base;
}

export function exportUrl(sessionId: string, format: 'png' | 'jpeg' | 'pdf'): string {
  return `${apiUrl(`/storyboard/${sessionId}/export`)}?format=${format}`;
}

export interface Scene {
  scene_number: number;
  start_time: number;
  end_time: number;
  duration: number;
  frame_path: string;
  frame_filename: string;
  transcript: string;
  caption: string;
  enhanced_caption: string;
}

/** Panel = one visual cell in the storyboard (may be multiple per scene when caption is split) */
export interface Panel {
  scene_number: number;
  frame_filename: string;
  enhanced_caption: string;
  start_time?: number;
  end_time?: number;
  panel_index?: number;
}

export interface SceneMetadata {
  video_path: string;
  video_name: string;
  session_path: string;
  total_scenes: number;
  scenes: Scene[];
  /** Panels (multiple snippets per scene when captions are split) - used for grid display */
  panels?: Panel[];
  /** Narrative summary shown as subtitle (e.g. video title) */
  story_arc_summary?: string;
  storyboard_path?: string;
  storyboard_pdf_path?: string;
  storyboard_page_paths?: string[];
  processing_timestamp?: string;
  /** Video dimensions for aspect-ratio-aware layout (landscape vs portrait/shorts) */
  video_width?: number;
  video_height?: number;
}
