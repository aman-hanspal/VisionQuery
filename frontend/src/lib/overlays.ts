import type { Detection } from "./types";

// Show boxes from one sampled frame only, including sampled frames with no hits.
export function nearestSample(
  timestamps: number[],
  time: number,
  tolerance: number,
): number | null {
  let lo = 0;
  let hi = timestamps.length;
  while (lo < hi) {
    const mid = (lo + hi) >>> 1;
    if (timestamps[mid] < time) lo = mid + 1;
    else hi = mid;
  }
  const candidates = [timestamps[lo - 1], timestamps[lo]].filter(
    (t) => t !== undefined,
  );
  const nearest = candidates.sort(
    (a, b) => Math.abs(a - time) - Math.abs(b - time),
  )[0];
  return nearest !== undefined && Math.abs(nearest - time) <= tolerance
    ? nearest
    : null;
}

export function indexDetections(
  detections: Detection[],
): Map<number, Detection[]> {
  const index = new Map<number, Detection[]>();
  for (const detection of detections) {
    if (detection.t === undefined) continue;
    const bucket = index.get(detection.t) ?? [];
    bucket.push(detection);
    index.set(detection.t, bucket);
  }
  return index;
}
