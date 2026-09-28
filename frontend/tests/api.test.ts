import { afterEach, expect, it, vi } from "vitest";
import { runQuery } from "@/lib/api";

afterEach(() => vi.unstubAllGlobals());
it("renders FastAPI validation errors as readable text", async () => {
  vi.stubGlobal(
    "fetch",
    vi
      .fn()
      .mockResolvedValue(
        new Response(
          JSON.stringify({
            detail: [{ loc: ["body", "fps"], msg: "must be positive" }],
          }),
          { status: 422 },
        ),
      ),
  );
  await expect(runQuery({ video_id: "test", fps: -1 })).rejects.toThrow(
    "body.fps: must be positive",
  );
});
