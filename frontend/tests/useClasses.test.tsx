import { act, cleanup, renderHook } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { useClasses } from "@/hooks/useClasses";
import { resolveClasses } from "@/lib/api";

vi.mock("@/lib/api", () => ({ resolveClasses: vi.fn() }));
beforeEach(() => {
  vi.useFakeTimers();
  vi.mocked(resolveClasses).mockReset();
});
afterEach(() => {
  cleanup();
  vi.useRealTimers();
});

it("withholds old classes immediately when prompt changes", async () => {
  vi.mocked(resolveClasses)
    .mockResolvedValueOnce({ classes: ["car"] })
    .mockResolvedValueOnce({ classes: ["dog"] });
  const { result, rerender } = renderHook(({ prompt }) => useClasses(prompt), {
    initialProps: { prompt: "car" },
  });
  await act(async () => {
    await vi.advanceTimersByTimeAsync(450);
  });
  expect(result.current.promptClasses).toEqual(["car"]);
  rerender({ prompt: "dog" });
  expect(result.current.promptClasses).toEqual([]);
  expect(result.current.classesBusy).toBe(true);
  await act(async () => {
    await vi.advanceTimersByTimeAsync(450);
  });
  expect(result.current.promptClasses).toEqual(["dog"]);
});

it("ignores late responses even if the request did not honor abort", async () => {
  let finishOld!: (value: { classes: string[] }) => void;
  vi.mocked(resolveClasses).mockImplementationOnce(
    () =>
      new Promise((resolve) => {
        finishOld = resolve;
      }),
  );
  vi.mocked(resolveClasses).mockResolvedValueOnce({ classes: ["dog"] });
  const { result, rerender } = renderHook(({ prompt }) => useClasses(prompt), {
    initialProps: { prompt: "car" },
  });
  await act(async () => {
    await vi.advanceTimersByTimeAsync(450);
  });
  rerender({ prompt: "dog" });
  await act(async () => {
    await vi.advanceTimersByTimeAsync(450);
  });
  await act(async () => {
    finishOld({ classes: ["car"] });
  });
  expect(result.current.promptClasses).toEqual(["dog"]);
  expect(result.current.classesBusy).toBe(false);
});

it("clears classes and busy state when prompt is emptied", async () => {
  vi.mocked(resolveClasses).mockResolvedValue({ classes: ["car"] });
  const { result, rerender } = renderHook(({ prompt }) => useClasses(prompt), {
    initialProps: { prompt: "car" },
  });
  await act(async () => {
    await vi.advanceTimersByTimeAsync(450);
  });
  rerender({ prompt: " " });
  expect(result.current.promptClasses).toEqual([]);
  expect(result.current.classesBusy).toBe(false);
});

it("reports resolution failure without silently using different classes", async () => {
  vi.mocked(resolveClasses).mockRejectedValue(new Error("Backend unavailable"));
  const { result } = renderHook(() => useClasses("car"));
  await act(async () => {
    await vi.advanceTimersByTimeAsync(450);
  });
  expect(result.current.promptClasses).toEqual([]);
  expect(result.current.classesBusy).toBe(false);
  expect(result.current.classesError).toBe("Backend unavailable");
});

it("retries failed resolution without changing the prompt", async () => {
  vi.mocked(resolveClasses)
    .mockRejectedValueOnce(new Error("offline"))
    .mockResolvedValueOnce({ classes: ["car"] });
  const { result } = renderHook(() => useClasses("car"));
  await act(async () => { await vi.advanceTimersByTimeAsync(450); });
  act(() => { result.current.retryClasses(); });
  expect(result.current.classesBusy).toBe(true);
  await act(async () => { await vi.advanceTimersByTimeAsync(450); });
  expect(result.current.classesError).toBe("");
  expect(result.current.promptClasses).toEqual(["car"]);
});
