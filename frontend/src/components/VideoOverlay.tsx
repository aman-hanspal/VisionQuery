"use client";

import {
  forwardRef,
  useCallback,
  useEffect,
  useImperativeHandle,
  useMemo,
  useRef,
} from "react";
import type { Detection } from "@/lib/types";
import { indexDetections, nearestSample } from "@/lib/overlays";
import { getDpr, labelColor } from "@/lib/utils";

interface VideoOverlayProps {
  videoSrc: string;
  detections: Detection[];
  fps: number;
  selectedTimestamps?: number[];
}

export const VideoOverlay = forwardRef<HTMLVideoElement, VideoOverlayProps>(
  function VideoOverlay(
    { videoSrc, detections, fps, selectedTimestamps },
    ref,
  ) {
    const videoRef = useRef<HTMLVideoElement>(null);
    const canvasRef = useRef<HTMLCanvasElement>(null);
    const wrapRef = useRef<HTMLDivElement>(null);
    const rafRef = useRef<number>(0);

    useImperativeHandle(ref, () => videoRef.current!, []);

    const detIndex = useMemo(() => indexDetections(detections), [detections]);
    const sampleTimes = useMemo(
      () => selectedTimestamps ?? [...detIndex.keys()].sort((a, b) => a - b),
      [selectedTimestamps, detIndex],
    );
    const tolerance = Math.min(0.25, 0.5 / (fps || 1));
    const getActive = useCallback(
      (time: number) => {
        const t = nearestSample(sampleTimes, time, tolerance);
        return t === null ? [] : (detIndex.get(t) ?? []);
      },
      [detIndex, sampleTimes, tolerance],
    );

    const draw = useCallback(() => {
      const video = videoRef.current;
      const canvas = canvasRef.current;
      if (!video || !canvas) return;

      const vw = video.videoWidth;
      const vh = video.videoHeight;
      if (!vw || !vh) return;

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

      const active = getActive(video.currentTime);
      if (active.length === 0) return;

      const sx = cw / vw;
      const sy = ch / vh;

      for (const d of active) {
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
    }, [getActive]);

    useEffect(() => {
      const video = videoRef.current;
      if (!video) return;

      const animLoop = () => {
        draw();
        rafRef.current = requestAnimationFrame(animLoop);
      };
      const onPlay = () => {
        cancelAnimationFrame(rafRef.current);
        animLoop();
      };
      const onPause = () => cancelAnimationFrame(rafRef.current);
      const onSeeked = () => draw();
      const onLoaded = () => draw();

      const observer = new ResizeObserver(draw);
      observer.observe(video);
      if (!video.paused) onPlay();
      video.addEventListener("play", onPlay);
      video.addEventListener("pause", onPause);
      video.addEventListener("ended", onPause);
      video.addEventListener("seeked", onSeeked);
      video.addEventListener("loadedmetadata", onLoaded);

      return () => {
        observer.disconnect();
        cancelAnimationFrame(rafRef.current);
        video.removeEventListener("play", onPlay);
        video.removeEventListener("pause", onPause);
        video.removeEventListener("ended", onPause);
        video.removeEventListener("seeked", onSeeked);
        video.removeEventListener("loadedmetadata", onLoaded);
      };
    }, [draw]);

    // Redraw when detections change
    useEffect(() => {
      draw();
    }, [detections, draw]);

    return (
      <div ref={wrapRef} className="relative w-full">
        <video
          ref={videoRef}
          src={videoSrc}
          controls
          playsInline
          className="w-full rounded-lg"
          style={{ display: "block" }}
        />
        <canvas
          ref={canvasRef}
          className="absolute top-0 left-0 pointer-events-none rounded-lg"
        />
      </div>
    );
  },
);
