import { useEffect, useState } from 'react';
import { getScenes, type SceneMetadata } from '../api/client';
import { SceneCard } from './SceneCard';

interface BentoGridProps {
  sessionId: string;
}

export function BentoGrid({ sessionId }: BentoGridProps) {
  const [metadata, setMetadata] = useState<SceneMetadata | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getScenes(sessionId)
      .then(setMetadata)
      .catch((e) => setError(e instanceof Error ? e.message : 'Failed to load'));
  }, [sessionId]);

  if (error) return <div className="bento-error">{error}</div>;
  if (!metadata) return <div className="bento-loading">Loading scenes…</div>;

  const scenes = metadata.scenes ?? [];
  if (scenes.length === 0) return <div className="bento-empty">No scenes found.</div>;

  return (
    <div className="bento-grid-container">
      <h2 className="bento-title">{metadata.video_name ?? 'Storyboard'} — {scenes.length} scenes</h2>
      <div className="bento-grid">
        {scenes.map((scene) => (
          <SceneCard
            key={scene.scene_number}
            scene={scene}
            sessionId={sessionId}
          />
        ))}
      </div>
    </div>
  );
}
