import { useEffect, useState } from 'react';
import { listSessions, deleteSession, type SessionInfo } from '../api/client';
import { getSavedSessionIds, unsaveSession } from '../utils/savedStoryboards';
import { storyboardUrl } from '../api/client';

interface SavedStoryboardsProps {
  onSelectSession: (sessionId: string) => void;
  onBack?: () => void;
  inline?: boolean;
}

function formatDate(ts: string): string {
  if (!ts) return '';
  try {
    const d = new Date(ts);
    return isNaN(d.getTime()) ? ts : d.toLocaleDateString(undefined, {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    });
  } catch {
    return ts;
  }
}

export function SavedStoryboards({ onSelectSession, onBack, inline }: SavedStoryboardsProps) {
  const [sessions, setSessions] = useState<SessionInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [savedIds, setSavedIds] = useState<string[]>(() => getSavedSessionIds());
  const [deletingId, setDeletingId] = useState<string | null>(null);

  const handleDelete = async (e: React.MouseEvent, sessionId: string) => {
    e.stopPropagation();
    if (!window.confirm('Delete this storyboard? This cannot be undone.')) return;
    setDeletingId(sessionId);
    try {
      await deleteSession(sessionId);
      unsaveSession(sessionId);
      setSessions((prev) => prev.filter((s) => s.session_id !== sessionId));
      setSavedIds((prev) => prev.filter((id) => id !== sessionId));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Delete failed');
    } finally {
      setDeletingId(null);
    }
  };

  useEffect(() => {
    listSessions()
      .then((list) => {
        const saved = getSavedSessionIds();
        setSavedIds(saved);
        list.sort((a, b) => {
          const aSaved = saved.includes(a.session_id) ? 1 : 0;
          const bSaved = saved.includes(b.session_id) ? 1 : 0;
          if (bSaved !== aSaved) return bSaved - aSaved;
          const ta = a.processing_timestamp || '';
          const tb = b.processing_timestamp || '';
          return tb.localeCompare(ta);
        });
        setSessions(list);
      })
      .catch((e) => setError(e instanceof Error ? e.message : 'Failed to load'))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="saved-loading">Loading saved storyboards…</div>;
  if (error) return <div className="saved-error">{error}</div>;

  if (sessions.length === 0) {
    return (
      <div className="saved-empty">
        <p>No saved storyboards yet.</p>
        <p className="saved-empty-hint">Paste a URL or upload a video above to generate one.</p>
        {!inline && onBack && (
          <button type="button" className="btn-secondary" onClick={onBack}>
            Go back
          </button>
        )}
      </div>
    );
  }

  return (
    <div className={`saved-storyboards ${inline ? 'saved-storyboards-inline' : ''}`}>
      <div className="saved-header">
        {!inline && onBack && (
          <button type="button" className="btn-secondary" onClick={onBack}>
            ← Back
          </button>
        )}
        <h2 className="saved-title">Saved storyboards</h2>
      </div>
      <div className="saved-grid">
        {sessions.map((s) => (
          <div
            key={s.session_id}
            role="button"
            tabIndex={0}
            className="saved-card"
            onClick={() => onSelectSession(s.session_id)}
            onKeyDown={(e) => e.key === 'Enter' && onSelectSession(s.session_id)}
          >
            <button
              type="button"
              className="saved-card-delete"
              onClick={(e) => handleDelete(e, s.session_id)}
              disabled={deletingId === s.session_id}
              title="Delete storyboard"
              aria-label="Delete storyboard"
            >
              {deletingId === s.session_id ? '…' : '×'}
            </button>
            <div className="saved-card-thumb">
              <img
                src={storyboardUrl(s.session_id)}
                alt={s.video_name}
                loading="lazy"
              />
            </div>
            <div className="saved-card-info">
              <span className="saved-card-name">{s.video_name}</span>
              <span className="saved-card-meta">
                {s.total_panels ?? s.total_scenes} panels · {formatDate(s.processing_timestamp)}
              </span>
              {savedIds.includes(s.session_id) && (
                <span className="saved-badge">Saved</span>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
