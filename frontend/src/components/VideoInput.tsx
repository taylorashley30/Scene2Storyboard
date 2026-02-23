import { useState, useRef } from "react";
import { processYoutube, processUpload } from "../api/client";

interface VideoInputProps {
  onSuccess: (sessionId: string) => void;
  onError: (message: string) => void;
}

export function VideoInput({ onSuccess, onError }: VideoInputProps) {
  const [url, setUrl] = useState("");
  const [loading, setLoading] = useState(false);
  const [mode, setMode] = useState<"url" | "upload">("url");
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleSubmitUrl = async () => {
    const u = url.trim();
    if (!u) {
      onError("Please enter a YouTube or Instagram URL");
      return;
    }
    setLoading(true);
    try {
      const res = await processYoutube(u);
      const sessionId = res.session_path.split(/[/\\]/).pop() ?? "";
      onSuccess(sessionId);
    } catch (e) {
      onError(e instanceof Error ? e.message : "Processing failed");
    } finally {
      setLoading(false);
    }
  };

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setLoading(true);
    try {
      const res = await processUpload(file);
      const sessionId = res.session_path.split(/[/\\]/).pop() ?? "";
      onSuccess(sessionId);
    } catch (e) {
      onError(e instanceof Error ? e.message : "Upload failed");
    } finally {
      setLoading(false);
    }
    e.target.value = "";
  };

  return (
    <div className="video-input">
      <div className="video-input-tabs">
        <button
          type="button"
          className={mode === "url" ? "active" : ""}
          onClick={() => setMode("url")}
        >
          Paste URL
        </button>
        <button
          type="button"
          className={mode === "upload" ? "active" : ""}
          onClick={() => setMode("upload")}
        >
          Upload Video
        </button>
      </div>
      {mode === "url" ? (
        <div className="video-input-url">
          <input
            type="text"
            placeholder="Video Link"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleSubmitUrl()}
            disabled={loading}
          />
          <button type="button" onClick={handleSubmitUrl} disabled={loading}>
            {loading ? "Processing…" : "Generate Storyboard"}
          </button>
        </div>
      ) : (
        <div className="video-input-upload">
          <input
            ref={fileInputRef}
            type="file"
            accept="video/*"
            onChange={handleUpload}
            disabled={loading}
            hidden
          />
          <button
            type="button"
            onClick={() => fileInputRef.current?.click()}
            disabled={loading}
          >
            {loading ? "Processing…" : "Choose video file"}
          </button>
        </div>
      )}
    </div>
  );
}
