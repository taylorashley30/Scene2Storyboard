import { useState } from 'react';
import { exportUrl } from '../api/client';

interface ExportControlsProps {
  sessionId: string;
}

export function ExportControls({ sessionId }: ExportControlsProps) {
  const [exporting, setExporting] = useState<string | null>(null);

  const handleExport = async (format: 'png' | 'jpeg' | 'pdf') => {
    setExporting(format);
    try {
      const url = exportUrl(sessionId, format);
      const res = await fetch(url);
      if (!res.ok) throw new Error('Export failed');
      const blob = await res.blob();
      const href = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = href;
      a.download = `storyboard.${format}`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(href);
    } catch {
      // Fallback: open in new tab
      window.open(exportUrl(sessionId, format), '_blank');
    } finally {
      setExporting(null);
    }
  };

  return (
    <div className="export-controls">
      <span className="export-label">Download as:</span>
      <button
        type="button"
        onClick={() => handleExport('png')}
        disabled={!!exporting}
      >
        {exporting === 'png' ? '…' : 'PNG'}
      </button>
      <button
        type="button"
        onClick={() => handleExport('jpeg')}
        disabled={!!exporting}
      >
        {exporting === 'jpeg' ? '…' : 'JPEG'}
      </button>
      <button
        type="button"
        onClick={() => handleExport('pdf')}
        disabled={!!exporting}
      >
        {exporting === 'pdf' ? '…' : 'PDF'}
      </button>
    </div>
  );
}
