import { act, cleanup, render } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { StrictMode } from "react";
import LiveOverlay from "@/components/LiveOverlay";

vi.mock("@/lib/api", () => ({ runLiveDetect: vi.fn() }));
beforeEach(() => {
  vi.stubGlobal(
    "ResizeObserver",
    class {
      observe() {}
      disconnect() {}
    },
  );
  vi.spyOn(HTMLCanvasElement.prototype, "getContext").mockReturnValue(null);
  vi.spyOn(HTMLMediaElement.prototype, "play").mockResolvedValue();
  vi.spyOn(HTMLMediaElement.prototype, "pause").mockImplementation(() => {});
});
afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

it("stops a camera stream that resolves after unmount", async () => {
  let grant!: (stream: MediaStream) => void;
  const stop = vi.fn();
  const getUserMedia = vi.fn(
    () =>
      new Promise<MediaStream>((resolve) => {
        grant = resolve;
      }),
  );
  Object.defineProperty(navigator, "mediaDevices", {
    configurable: true,
    value: { getUserMedia },
  });
  const { unmount } = render(
    <LiveOverlay
      classes={["person"]}
      conf={0}
      sampleFps={1}
      onDetections={() => {}}
    />,
  );
  unmount();
  await act(async () => {
    grant({ getTracks: () => [{ stop }] } as unknown as MediaStream);
  });
  expect(stop).toHaveBeenCalled();
});

it("stops the stale Strict Mode stream without replacing the active one", async () => {
  const grants: Array<(stream: MediaStream) => void> = [];
  const oldStop = vi.fn();
  const currentStop = vi.fn();
  const getUserMedia = vi.fn(
    () =>
      new Promise<MediaStream>((resolve) => {
        grants.push(resolve);
      }),
  );
  Object.defineProperty(navigator, "mediaDevices", {
    configurable: true,
    value: { getUserMedia },
  });
  const { container, unmount } = render(
    <StrictMode>
      <LiveOverlay
        classes={["person"]}
        conf={0}
        sampleFps={1}
        onDetections={() => {}}
      />
    </StrictMode>,
  );
  expect(grants).toHaveLength(2);
  const current = {
    getTracks: () => [{ stop: currentStop }],
  } as unknown as MediaStream;
  await act(async () => {
    grants[1](current);
  });
  await act(async () => {
    grants[0]({
      getTracks: () => [{ stop: oldStop }],
    } as unknown as MediaStream);
  });
  expect(oldStop).toHaveBeenCalled();
  expect(container.querySelector("video")!.srcObject).toBe(current);
  expect(currentStop).not.toHaveBeenCalled();
  unmount();
  expect(currentStop).toHaveBeenCalled();
});
