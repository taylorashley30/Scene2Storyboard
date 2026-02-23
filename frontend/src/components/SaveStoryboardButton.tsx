import { useState, useEffect } from 'react';
import { isSessionSaved, saveSession } from '../utils/savedStoryboards';

interface SaveStoryboardButtonProps {
  sessionId: string;
}

export function SaveStoryboardButton({ sessionId }: SaveStoryboardButtonProps) {
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    setSaved(isSessionSaved(sessionId));
  }, [sessionId]);

  const handleClick = () => {
    saveSession(sessionId);
    setSaved(true);
  };

  if (saved) {
    return (
      <span className="save-badge saved">
        Saved to my list
      </span>
    );
  }

  return (
    <button
      type="button"
      className="btn-save"
      onClick={handleClick}
      title="Add to saved storyboards"
    >
      Save storyboard
    </button>
  );
}
