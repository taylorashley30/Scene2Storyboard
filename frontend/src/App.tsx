import { useState } from "react";
import { VideoInput } from "./components/VideoInput";
import { BentoGrid } from "./components/BentoGrid";
import { ExportControls } from "./components/ExportControls";
import { SavedStoryboards } from "./components/SavedStoryboards";
import { SaveStoryboardButton } from "./components/SaveStoryboardButton";
import "./App.css";

function App() {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [showSaved, setShowSaved] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const goHome = () => {
    setSessionId(null);
    setShowSaved(false);
    setError(null);
  };

  return (
    <div className="app">
      <header className="app-header">
        <img src="/favicon.png" alt="" className="app-logo" />
        <h1>Scene2Storyboard</h1>
        <p>Turn videos into visual storyboards</p>
      </header>

      {sessionId ? (
        <main className="app-main app-main-storyboard">
          <div className="app-storyboard-actions">
            <button type="button" className="btn-secondary" onClick={goHome}>
              ← Home
            </button>
            <div className="app-storyboard-right">
              <SaveStoryboardButton sessionId={sessionId} />
              <ExportControls sessionId={sessionId} />
            </div>
          </div>
          <BentoGrid sessionId={sessionId} />
        </main>
      ) : (
        <main className="app-main app-main-home">
          <VideoInput
            onSuccess={(id) => {
              setSessionId(id);
              setError(null);
            }}
            onError={setError}
          />
          {error && <div className="app-error">{error}</div>}
          <div className="saved-toggle-wrap">
            <button
              type="button"
              className="saved-toggle-link"
              onClick={() => setShowSaved(!showSaved)}
            >
              {showSaved ? "Hide saved storyboards" : "View saved storyboards"}
            </button>
          </div>
          {showSaved && (
            <SavedStoryboards
              onSelectSession={(id) => setSessionId(id)}
              onBack={() => setShowSaved(false)}
              inline
            />
          )}
        </main>
      )}
    </div>
  );
}

export default App;
