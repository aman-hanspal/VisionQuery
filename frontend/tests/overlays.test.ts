import { expect, it } from "vitest";
import { indexDetections, nearestSample } from "@/lib/overlays";

it("uses the negative sampled frame instead of neighboring detections", () => {
  const index = indexDetections([
    { t: 0, label: "car", conf: 0.9, bbox: [0, 0, 10, 10] },
  ]);
  const time = nearestSample([0, 0.1], 0.09, 0.25);
  expect(time).toBe(0.1);
  expect(index.get(time!) ?? []).toEqual([]);
});

it("does not merge neighboring frames or show boxes across long gaps", () => {
  expect(nearestSample([0, 1, 10], 0.95, 0.25)).toBe(1);
  expect(nearestSample([0, 1, 10], 5, 0.25)).toBeNull();
  expect(nearestSample([], 0, 0.25)).toBeNull();
});
