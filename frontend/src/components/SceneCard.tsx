import type { Scene } from '../api/client';
import { frameUrl } from '../api/client';

interface SceneCardProps {
  scene: Scene;
  sessionId: string;
}

export function SceneCard({ scene, sessionId }: SceneCardProps) {
  const src = frameUrl(sessionId, scene.frame_filename);
  return (
    <div className="scene-card">
      <div className="scene-card-image">
        <img src={src} alt={`Scene ${scene.scene_number}`} loading="lazy" />
      </div>
      <div className="scene-card-caption">
        {scene.enhanced_caption || scene.caption || `Scene ${scene.scene_number}`}
      </div>
    </div>
  );
}
