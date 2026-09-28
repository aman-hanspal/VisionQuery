"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type { Detection } from "@/lib/types";
import { runLiveDetect } from "@/lib/api";
import { getDpr, labelColor } from "@/lib/utils";

interface LiveOverlayProps {
  classes: string[];
  conf: number;
  sampleFps: number;
  onDetections: (detections: Detection[]) => void;
}

export default function LiveOverlay({
  classes,
  conf,
  sampleFps,
  onDetections,
}: LiveOverlayProps) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const captureRef = useRef<HTMLCanvasElement>(null);
  const [status, setStatus] = useState<"starting" | "active" | "error">(
    "starting",
  );
  const [cameraError, setCameraError] = useState("");
  const [result, setResult] = useState<{
    key: string;
    detections: Detection[];
    size: { w: number; h: number } | null;
    error: string;
  } | null>(null);
  const queryKey = JSON.stringify([classes, conf]);
  const valid =
    classes.length > 0 &&
    Number.isFinite(conf) &&
    conf >= 0 &&
    conf <= 1 &&
    Number.isFinite(sampleFps) &&
    sampleFps > 0 &&
    sampleFps <= 240;
  const onDetectionsRef = useRef(onDetections);
  useEffect(() => {
    onDetectionsRef.current = onDetections;
  }, [onDetections]);

  useEffect(() => {
    let stream: MediaStream | null = null;
    let active = true;
    const video = videoRef.current;
    (async () => {
      try {
        stream = await navigator.mediaDevices.getUserMedia({
          video: true,
          audio: false,
        });
        if (!active || !video) {
          stream.getTracks().forEach((track) => track.stop());
          return;
        }
        video.srcObject = stream;
        await video.play();
        if (active) setStatus("active");
      } catch (error) {
        stream?.getTracks().forEach((track) => track.stop());
        if (active) {
          setCameraError(
            error instanceof Error ? error.message : String(error),
          );
          setStatus("error");
        }
      }
    })();
    return () => {
      active = false;
      if (video) {
        video.pause();
        video.srcObject = null;
      }
      stream?.getTracks().forEach((track) => track.stop());
    };
  }, []);

  useEffect(() => {
    onDetectionsRef.current([]);
    if (status !== "active" || !valid) return;
    let stopped = false;
    let timer: ReturnType<typeof setTimeout>;
    const controller = new AbortController();
    const targetMs = Math.max(120, 1000 / sampleFps);
    async function loop() {
      const start = performance.now();
      try {
        const video = videoRef.current;
        const cap = captureRef.current;
        if (
          !video ||
          !cap ||
          video.readyState < 2 ||
          !video.videoWidth ||
          !video.videoHeight
        )
          return;
        const scale = Math.min(1, 640 / video.videoWidth);
        cap.width = Math.max(1, Math.round(video.videoWidth * scale));
        cap.height = Math.max(1, Math.round(video.videoHeight * scale));
        const ctx = cap.getContext("2d");
        if (!ctx) return;
        ctx.drawImage(video, 0, 0, cap.width, cap.height);
        const image_b64 = cap.toDataURL("image/jpeg", 0.6).split(",")[1];
        const data = await runLiveDetect(
          { image_b64, classes, conf },
          controller.signal,
        );
        if (!stopped) {
          setResult({
            key: queryKey,
            detections: data.detections,
            size: { w: data.frame_width, h: data.frame_height },
            error: "",
          });
          onDetectionsRef.current(data.detections);
        }
      } catch (error) {
        if (!stopped) {
          setResult({
            key: queryKey,
            detections: [],
            size: null,
            error: error instanceof Error ? error.message : String(error),
          });
          onDetectionsRef.current([]);
        }
      } finally {
        if (!stopped)
          timer = setTimeout(
            loop,
            Math.max(100, targetMs - (performance.now() - start)),
          );
      }
    }
    void loop();
    return () => {
      stopped = true;
      clearTimeout(timer);
      controller.abort();
    };
  }, [status, valid, classes, conf, sampleFps, queryKey]);

  // Draw detections on canvas
  const drawDetections = useCallback(() => {
    const video = videoRef.current;
    const canvas = canvasRef.current;
    if (!video || !canvas) return;

    const rect = video.getBoundingClientRect();
    const cw = rect.width;
    const ch = rect.height;

    const dpr = getDpr();
    canvas.width = cw * dpr;
    canvas.height = ch * dpr;
    canvas.style.width = `${cw}px`;
    canvas.style.height = `${ch}px`;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    ctx.scale(dpr, dpr);
    ctx.clearRect(0, 0, cw, ch);

    if (
      !valid ||
      result?.key !== queryKey ||
      !result.size ||
      !result.detections.length
    )
      return;
    const frameSize = result.size;
    const detections = result.detections;

    const sx = cw / frameSize.w;
    const sy = ch / frameSize.h;

    for (const d of detections.slice(0, 10)) {
      const [x1, y1, x2, y2] = d.bbox;
      const dx = x1 * sx;
      const dy = y1 * sy;
      const dw = (x2 - x1) * sx;
      const dh = (y2 - y1) * sy;

      const color = labelColor(d.label);
      const lw = 1.5 + d.conf * 2.5;

      ctx.strokeStyle = color;
      ctx.lineWidth = Math.min(lw, 4);
      ctx.strokeRect(dx, dy, dw, dh);

      const text = `${d.label} (${d.conf.toFixed(2)})`;
      ctx.font = "bold 12px system-ui, sans-serif";
      const tm = ctx.measureText(text);
      const th = 16;

      ctx.fillStyle = "rgba(0,0,0,0.7)";
      ctx.fillRect(dx, dy - th - 2, tm.width + 8, th + 2);
      ctx.fillStyle = "#fff";
      ctx.fillText(text, dx + 4, dy - 4);
    }
  }, [result, queryKey, valid]);

  useEffect(() => {
    drawDetections();
    const observer = new ResizeObserver(drawDetections);
    if (videoRef.current) observer.observe(videoRef.current);
    return () => observer.disconnect();
  }, [drawDetections]);

  return (
    <div className="relative w-full">
      <video
        ref={videoRef}
        playsInline
        muted
        className="w-full rounded-lg bg-black"
        style={{ display: "block" }}
      />
      <canvas
        ref={canvasRef}
        className="absolute top-0 left-0 pointer-events-none rounded-lg"
      />
      <canvas ref={captureRef} className="hidden" />
      <div className="absolute top-2 left-2 px-2 py-1 rounded text-xs text-white bg-black/50">
        {status === "error"
          ? `Webcam error: ${cameraError}`
          : status !== "active"
            ? "Starting..."
            : !valid
              ? "Waiting for valid classes and settings..."
              : result?.key === queryKey && result.error
                ? `Detection error: ${result.error}`
                : "Live detecting..."}
      </div>
    </div>
  );
}
