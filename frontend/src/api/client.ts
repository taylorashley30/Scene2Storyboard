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

export async function getScenes(sessionId: string): Promise<SceneMetadata> {
  const res = await fetch(apiUrl(`/scenes/${sessionId}`));
  if (!res.ok) throw new Error('Session not found');
  return res.json();
}

export function frameUrl(sessionId: string, frameFilename: string): string {
  return apiUrl(`/frame/${sessionId}/${frameFilename}`);
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

export interface SceneMetadata {
  video_path: string;
  video_name: string;
  session_path: string;
  total_scenes: number;
  scenes: Scene[];
  storyboard_path?: string;
  processing_timestamp?: string;
}
