import { useState } from 'react';
import { VideoInput } from './components/VideoInput';
import { BentoGrid } from './components/BentoGrid';
import { ExportControls } from './components/ExportControls';
import './App.css';

function App() {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  return (
    <div className="app">
      <header className="app-header">
        <h1>Scene2Storyboard</h1>
        <p>Turn videos into comic-style storyboards</p>
      </header>

      {!sessionId ? (
        <main className="app-main">
          <VideoInput
            onSuccess={(id) => {
              setSessionId(id);
              setError(null);
            }}
            onError={setError}
          />
          {error && <div className="app-error">{error}</div>}
        </main>
      ) : (
        <main className="app-main app-main-storyboard">
          <div className="app-storyboard-actions">
            <button
              type="button"
              className="btn-secondary"
              onClick={() => {
                setSessionId(null);
                setError(null);
              }}
            >
              New video
            </button>
            <ExportControls sessionId={sessionId} />
          </div>
          <BentoGrid sessionId={sessionId} />
        </main>
      )}
    </div>
  );
}

export default App;
