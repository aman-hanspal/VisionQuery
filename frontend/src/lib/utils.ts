export function getDpr(): number {
  return typeof window === "undefined"
    ? 1
    : Math.max(1, window.devicePixelRatio || 1);
}

export function labelColor(label: string): string {
  let hash = 0;
  for (const char of label) hash = (hash * 31 + char.charCodeAt(0)) | 0;
  return `hsl(${Math.abs(hash) % 360} 80% 55%)`;
}

export function detectionAccent(confidence: number): string {
  return confidence >= 0.75
    ? "#16a34a"
    : confidence >= 0.5
      ? "#2563eb"
      : "#d97706";
}

export function formatTime(seconds: number): string {
  const t = Math.max(0, Number.isFinite(seconds) ? seconds : 0);
  const minutes = Math.floor(t / 60);
  return `${minutes}:${(t % 60).toFixed(2).padStart(5, "0")}`;
}
