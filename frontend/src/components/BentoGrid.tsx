import { useEffect, useState } from 'react';
import { getScenes, type SceneMetadata, type Panel, type Scene } from '../api/client';
import { SceneCard } from './SceneCard';
import { PanelModal } from './PanelModal';

interface BentoGridProps {
  sessionId: string;
}

function toDisplayItems(metadata: SceneMetadata): { frameFilename: string; caption: string; label: string }[] {
  const panels = metadata.panels;
  if (panels && panels.length > 0) {
    return panels.map((p: Panel, i: number) => ({
      frameFilename: p.frame_filename,
      caption: p.enhanced_caption || '',
      label: `Panel ${i + 1}`,
    }));
  }
  const scenes = metadata.scenes ?? [];
  return scenes.map((s: Scene) => ({
    frameFilename: s.frame_filename,
    caption: s.enhanced_caption || s.caption || '',
    label: `Scene ${s.scene_number}`,
  }));
}

export function BentoGrid({ sessionId }: BentoGridProps) {
  const [metadata, setMetadata] = useState<SceneMetadata | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [modalItem, setModalItem] = useState<{ frameFilename: string; caption: string; label: string } | null>(null);

  useEffect(() => {
    getScenes(sessionId)
      .then(setMetadata)
      .catch((e) => setError(e instanceof Error ? e.message : 'Failed to load'));
  }, [sessionId]);

  if (error) return <div className="bento-error">{error}</div>;
  if (!metadata) return <div className="bento-loading">Loading scenes…</div>;

  const scenes = metadata.scenes ?? [];
  const panels = metadata.panels ?? [];
  const items = toDisplayItems(metadata);
  if (items.length === 0) return <div className="bento-empty">No scenes found.</div>;

  const summary = metadata.story_arc_summary || metadata.video_name || '';
  const title = metadata.video_name ?? 'Storyboard';
  const countLabel = panels.length > 0 ? `${panels.length} panels` : `${scenes.length} scenes`;
  const w = metadata.video_width ?? 1920;
  const h = metadata.video_height ?? 1080;
  const isPortrait = h > w;

  return (
    <div className="bento-grid-container">
      <h2 className="bento-title">{title} — {countLabel}</h2>
      {summary && (
        <div className="bento-summary">
          {summary}
        </div>
      )}
      <div className={`bento-grid ${isPortrait ? 'bento-grid-portrait' : ''}`}>
        {items.map((item, i) => (
          <SceneCard
            key={i}
            frameFilename={item.frameFilename}
            caption={item.caption}
            label={item.label}
            sessionId={sessionId}
            isPortrait={isPortrait}
            onClick={() => setModalItem(item)}
          />
        ))}
      </div>
      {modalItem && (
        <PanelModal
          frameFilename={modalItem.frameFilename}
          caption={modalItem.caption}
          label={modalItem.label}
          sessionId={sessionId}
          isPortrait={isPortrait}
          onClose={() => setModalItem(null)}
        />
      )}
    </div>
  );
}
