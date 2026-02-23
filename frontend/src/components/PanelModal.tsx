import { useState, useCallback, useEffect } from 'react';
import { frameUrl } from '../api/client';

interface PanelModalProps {
  frameFilename: string;
  caption: string;
  label: string;
  sessionId: string;
  isPortrait?: boolean;
  onClose: () => void;
}

export function PanelModal({ frameFilename, caption, label, sessionId, isPortrait, onClose }: PanelModalProps) {
  const [zoom, setZoom] = useState(1);
  const [panning, setPanning] = useState(false);
  const [position, setPosition] = useState({ x: 0, y: 0 });
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 });

  const src = frameUrl(sessionId, frameFilename);

  const handleKeyDown = useCallback((e: KeyboardEvent) => {
    if (e.key === 'Escape') onClose();
  }, [onClose]);

  useEffect(() => {
    document.addEventListener('keydown', handleKeyDown);
    document.body.style.overflow = 'hidden';
    return () => {
      document.removeEventListener('keydown', handleKeyDown);
      document.body.style.overflow = '';
    };
  }, [handleKeyDown]);

  const zoomIn = () => setZoom((z) => Math.min(z + 0.5, 3));
  const zoomOut = () => setZoom((z) => Math.max(z - 0.5, 0.5));

  const handleMouseDown = (e: React.MouseEvent) => {
    if (zoom > 1) {
      setPanning(true);
      setDragStart({ x: e.clientX - position.x, y: e.clientY - position.y });
    }
  };

  const handleMouseMove = (e: React.MouseEvent) => {
    if (panning) {
      setPosition({ x: e.clientX - dragStart.x, y: e.clientY - dragStart.y });
    }
  };

  const handleMouseUp = () => setPanning(false);

  const handleWheel = (e: React.WheelEvent) => {
    e.preventDefault();
    const delta = e.deltaY > 0 ? -0.1 : 0.1;
    setZoom((z) => Math.max(0.5, Math.min(3, z + delta)));
  };

  return (
    <div
      className="panel-modal-overlay"
      onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}
      role="dialog"
      aria-modal
      aria-label={`Panel ${label}`}
    >
      <div className={`panel-modal ${isPortrait ? 'panel-modal-portrait' : ''}`} onClick={(e) => e.stopPropagation()}>
        <div className="panel-modal-header">
          <span className="panel-modal-label">{label}</span>
          <div className="panel-modal-zoom">
            <button type="button" onClick={zoomOut} title="Zoom out" aria-label="Zoom out">−</button>
            <span>{Math.round(zoom * 100)}%</span>
            <button type="button" onClick={zoomIn} title="Zoom in" aria-label="Zoom in">+</button>
          </div>
          <button
            type="button"
            className="panel-modal-close"
            onClick={onClose}
            aria-label="Close"
          >
            ×
          </button>
        </div>
        <div
          className="panel-modal-body"
          onMouseDown={handleMouseDown}
          onMouseMove={handleMouseMove}
          onMouseUp={handleMouseUp}
          onMouseLeave={handleMouseUp}
          onWheel={handleWheel}
          style={{ cursor: zoom > 1 ? (panning ? 'grabbing' : 'grab') : 'default' }}
        >
          <div
            className="panel-modal-image-wrap"
            style={{
              transform: `translate(${position.x}px, ${position.y}px) scale(${zoom})`,
            }}
          >
            <img src={src} alt={label} draggable={false} />
          </div>
        </div>
        <div className="panel-modal-caption">{caption}</div>
      </div>
    </div>
  );
}
