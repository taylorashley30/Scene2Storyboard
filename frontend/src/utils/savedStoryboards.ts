const STORAGE_KEY = 'scene2storyboard_saved';

export function getSavedSessionIds(): string[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

export function isSessionSaved(sessionId: string): boolean {
  return getSavedSessionIds().includes(sessionId);
}

export function saveSession(sessionId: string): void {
  const ids = getSavedSessionIds();
  if (ids.includes(sessionId)) return;
  ids.push(sessionId);
  localStorage.setItem(STORAGE_KEY, JSON.stringify(ids));
}

export function unsaveSession(sessionId: string): void {
  const ids = getSavedSessionIds().filter((id) => id !== sessionId);
  localStorage.setItem(STORAGE_KEY, JSON.stringify(ids));
}
