"use client";

interface QueryControlsProps {
  prompt: string;
  onPromptChange: (prompt: string) => void;
  displayClasses: string[];
  classesBusy: boolean;
  classCount: number;
  fps: number;
  onFpsChange: (fps: number) => void;
  conf: number;
  onConfChange: (conf: number) => void;
  onRunQuery: () => void;
  busy: boolean;
  mode: "video" | "live";
  videoId: string;
  scanMode: "full" | "budget";
  onScanModeChange: (mode: "full" | "budget") => void;
  frameBudget: number;
  onFrameBudgetChange: (value: number) => void;
}

export default function QueryControls({
  prompt,
  onPromptChange,
  displayClasses,
  classesBusy,
  classCount,
  fps,
  onFpsChange,
  conf,
  onConfChange,
  onRunQuery,
  busy,
  mode,
  videoId,
  scanMode,
  onScanModeChange,
  frameBudget,
  onFrameBudgetChange,
}: QueryControlsProps) {
  return (
    <div className="card mt-3">
      <div className="font-bold mb-2">Query Controls</div>
      <div className="grid gap-2.5">
        <label className="grid gap-1.5">
          <span className="text-sm">
            Objects to find (comma-separated; free-form with OpenRouter
            configured)
          </span>
          <input
            value={prompt}
            onChange={(e) => onPromptChange(e.target.value)}
            placeholder="person, knife"
            disabled={busy}
            className="input-field"
          />
        </label>

        <div className="grid gap-2">
          <div className="flex justify-between items-center gap-2.5">
            <div className="text-[13px] text-slate-700 font-bold">
              Classes used for detection
            </div>
            <div className="text-xs text-slate-500">
              {classesBusy
                ? "Extracting..."
                : classCount > 0
                  ? `${classCount} classes`
                  : "No classes"}
            </div>
          </div>
          <div className="flex flex-wrap gap-2">
            {displayClasses.map((c, i) => (
              <span key={`${c}-${i}`} className="chip">
                {c}
              </span>
            ))}
          </div>
        </div>

        {mode === "video" && (
          <div className="flex gap-3 flex-wrap">
            <label className="grid gap-1.5 text-sm">
              Scan mode
              <select
                className="input-field"
                disabled={busy}
                value={scanMode}
                onChange={(e) =>
                  onScanModeChange(e.target.value as "full" | "budget")
                }
              >
                <option value="full">Full video at sample FPS</option>
                <option value="budget">Frame budget across full video</option>
              </select>
            </label>
            {scanMode === "budget" && (
              <label className="grid gap-1.5 text-sm">
                Frame budget
                <input
                  className="input-field w-[140px]"
                  type="number"
                  min="2"
                  max="100000"
                  step="1"
                  disabled={busy}
                  value={frameBudget}
                  onChange={(e) => onFrameBudgetChange(Number(e.target.value))}
                />
              </label>
            )}
          </div>
        )}
        <div className="flex gap-3 flex-wrap">
          <label className="grid gap-1.5">
            <span className="text-sm">Sample FPS</span>
            <input
              type="number"
              min="0.1"
              max="240"
              step="0.1"
              value={fps}
              onChange={(e) => onFpsChange(Number(e.target.value))}
              disabled={busy || (mode === "video" && scanMode === "budget")}
              className="input-field w-[140px]"
            />
          </label>

          <label className="grid gap-1.5">
            <span className="text-sm">Conf</span>
            <input
              type="number"
              min="0"
              max="1"
              step="0.05"
              value={conf}
              onChange={(e) => onConfChange(Number(e.target.value))}
              disabled={busy}
              className="input-field w-[140px]"
            />
          </label>

          <div className="flex items-end">
            <button
              onClick={onRunQuery}
              disabled={
                mode !== "video" ||
                busy ||
                !videoId ||
                classesBusy ||
                !classCount ||
                !Number.isFinite(fps) ||
                fps <= 0 ||
                fps > 240 ||
                !Number.isFinite(conf) ||
                conf < 0 ||
                conf > 1 ||
                (scanMode === "budget" &&
                  (!Number.isInteger(frameBudget) ||
                    frameBudget < 2 ||
                    frameBudget > 100000))
              }
              className="btn-primary"
              title={mode === "live" ? "Live mode auto-runs detection" : ""}
            >
              {mode === "video"
                ? busy
                  ? "Working..."
                  : "Run Query"
                : "Auto Live"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
