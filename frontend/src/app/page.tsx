"use client";

import { useCallback, useRef, useState } from "react";
import { getVideoUrl, runQuery, uploadVideo } from "@/lib/api";
import type { Detection, ScanMetadata } from "@/lib/types";
import { useClasses } from "@/hooks/useClasses";
import Header from "@/components/Header";
import VideoUpload from "@/components/VideoUpload";
import QueryControls from "@/components/QueryControls";
import { VideoOverlay } from "@/components/VideoOverlay";
import LiveOverlay from "@/components/LiveOverlay";
import DetectionList from "@/components/DetectionList";
import ErrorDisplay from "@/components/ErrorDisplay";

export default function Home() {
  const videoRef = useRef<HTMLVideoElement>(null);

  const [videoId, setVideoId] = useState("");
  const [mode, setMode] = useState<"video" | "live">("video");
  const [prompt, setPrompt] = useState("person, knife");
  const [fps, setFps] = useState(1);
  const [conf, setConf] = useState(0.25);
  const [videoDetections, setVideoDetections] = useState<Detection[]>([]);
  const [liveDetections, setLiveDetections] = useState<Detection[]>([]);
  const [scan, setScan] = useState<ScanMetadata | null>(null);
  const [resultClasses, setResultClasses] = useState<string[]>([]);
  const [scanMode, setScanMode] = useState<"full" | "budget">("full");
  const [frameBudget, setFrameBudget] = useState(100);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const {
    promptClasses,
    displayClasses,
    classesBusy,
    classesError,
    retryClasses,
  } = useClasses(prompt);

  const videoUrl = videoId ? getVideoUrl(videoId) : "";

  const handleUpload = async (file: File) => {
    setError("");
    setBusy(true);
    try {
      const data = await uploadVideo(file);
      setVideoId(data.video_id);
      setVideoDetections([]);
      setScan(null);
      if (videoRef.current) {
        videoRef.current.currentTime = 0;
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  };

  const handleRunQuery = async () => {
    if (mode === "live" || classesBusy || !promptClasses.length) return;
    if (!videoId) {
      setError("Upload a video first.");
      return;
    }
    setError("");
    setBusy(true);
    setVideoDetections([]);
    setScan(null);
    try {
      const data = await runQuery({
        video_id: videoId,
        prompt,
        classes: [...promptClasses],
        scan_mode: scanMode,
        frame_budget: scanMode === "budget" ? frameBudget : undefined,
        fps: Number(fps),
        conf: Number(conf),
      });
      setVideoDetections(Array.isArray(data.detections) ? data.detections : []);
      setScan(data.metadata);
      setResultClasses(data.classes);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  };

  const seekTo = (t: number) => {
    if (mode !== "video") return;
    const v = videoRef.current;
    if (!v) return;
    v.currentTime = Number(t) || 0;
    void v.play().catch(() => {});
  };

  const handleLiveDetections = useCallback((next: Detection[]) => {
    setLiveDetections(Array.isArray(next) ? next : []);
  }, []);

  const detections = mode === "live" ? liveDetections : videoDetections;

  return (
    <div className="max-w-[1120px] mx-auto">
      <Header mode={mode} onModeChange={setMode} busy={busy} />

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 items-start">
        <div>
          {mode === "video" ? (
            <VideoUpload
              onUpload={handleUpload}
              busy={busy}
              videoId={videoId}
            />
          ) : (
            <div className="card">
              <div className="font-bold mb-2">Live Webcam</div>
              <div className="text-slate-500 text-sm">
                Live detection is running continuously with current
                classes/prompt.
              </div>
            </div>
          )}

          <QueryControls
            prompt={prompt}
            onPromptChange={setPrompt}
            displayClasses={displayClasses}
            classesBusy={classesBusy}
            classCount={promptClasses.length}
            fps={fps}
            onFpsChange={setFps}
            conf={conf}
            onConfChange={setConf}
            onRunQuery={handleRunQuery}
            busy={busy}
            mode={mode}
            videoId={videoId}
            scanMode={scanMode}
            onScanModeChange={setScanMode}
            frameBudget={frameBudget}
            onFrameBudgetChange={setFrameBudget}
          />

          <ErrorDisplay error={error || null} onDismiss={() => setError("")} />
          {classesError && (
            <div className="card mt-3 text-sm text-red-700" role="alert">
              <p>{classesError}</p>
              <button className="btn-primary mt-2" onClick={retryClasses}>
                Retry class extraction
              </button>
            </div>
          )}
        </div>

        <div>
          <div className="card">
            <div className="font-bold mb-2">
              {mode === "video" ? "Video" : "Live"}
            </div>
            {mode === "video" ? (
              videoId ? (
                <VideoOverlay
                  ref={videoRef}
                  videoSrc={videoUrl}
                  detections={videoDetections}
                  fps={scan?.effective_sample_fps || Number(fps) || 1}
                  selectedTimestamps={scan?.selected_timestamps}
                />
              ) : (
                <div className="text-slate-500">
                  Upload a video to preview it here.
                </div>
              )
            ) : (
              <LiveOverlay
                classes={promptClasses}
                conf={Number.isFinite(conf) ? conf : 0.25}
                sampleFps={Number(fps) || 1}
                onDetections={handleLiveDetections}
              />
            )}
          </div>

          {mode === "video" && scan && (
            <div className="card mt-3 text-sm" role="status">
              <p>
                {scan.scan_complete
                  ? "Scan completed"
                  : `Incomplete scan: ${scan.stop_reason}`}{" "}
                · {scan.detector_calls} frames sampled ·{" "}
                {scan.elapsed_seconds.toFixed(2)}s
              </p>
              <p>
                Classes: {resultClasses.join(", ")}. Sampling can miss objects
                between frames.
              </p>
              {scan.detections_truncated && (
                <p className="text-amber-700">
                  Showing {videoDetections.length} of {scan.total_detections}{" "}
                  detections. The result limit did not stop the scan.
                </p>
              )}
              {!scan.run_log_saved && (
                <p className="text-amber-700">Run log could not be saved.</p>
              )}
            </div>
          )}
          <DetectionList detections={detections} mode={mode} onSeek={seekTo} />
        </div>
      </div>
    </div>
  );
}
