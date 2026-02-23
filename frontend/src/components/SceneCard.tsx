import { frameUrl } from '../api/client';

/** Props for displaying a scene or panel (panel = snippet when caption is split) */
interface SceneCardProps {
  frameFilename: string;
  caption: string;
  label: string;
  sessionId: string;
  isPortrait?: boolean;
  onClick?: () => void;
}

export function SceneCard({ frameFilename, caption, label, sessionId, isPortrait, onClick }: SceneCardProps) {
  const src = frameUrl(sessionId, frameFilename);
  const Component = onClick ? 'button' : 'div';
  const cardClass = ['scene-card', onClick && 'scene-card-interactive', isPortrait && 'scene-card-portrait']
    .filter(Boolean).join(' ');
  const props = onClick ? { type: 'button' as const, onClick, className: cardClass } : { className: cardClass };
  return (
    <Component {...props}>
      <div className={`scene-card-image ${isPortrait ? 'scene-card-image-portrait' : ''}`}>
        <img src={src} alt={label} loading="lazy" />
      </div>
      <div className="scene-card-caption">
        {caption}
      </div>
    </Component>
  );
}
