"use client";

interface HeaderProps {
  busy: boolean;
  mode: "video" | "live";
  onModeChange: (mode: "video" | "live") => void;
}

export default function Header({ mode, onModeChange, busy }: HeaderProps) {
  return (
    <div
      className="mb-3.5 rounded-xl p-3.5 text-white"
      style={{
        background:
          "linear-gradient(120deg, #0f172a 0%, #1d4ed8 50%, #7c3aed 100%)",
      }}
    >
      <div className="flex justify-between gap-2.5 items-center flex-wrap">
        <div>
          <h1 className="m-0 text-3xl font-bold tracking-tight">VisionQuery</h1>
          <p className="mt-1.5 mb-0 opacity-90 text-sm">
            Natural-language search for video surveillance
          </p>
        </div>
        <div className="flex gap-2 items-center">
          <button
            disabled={busy}
            onClick={() => onModeChange("video")}
            className="px-2.5 py-1.5 rounded-full border border-white/35 text-white text-[13px] cursor-pointer"
            style={{
              background:
                mode === "video" ? "rgba(255,255,255,0.25)" : "transparent",
            }}
          >
            Video System
          </button>
          <button
            disabled={busy}
            onClick={() => onModeChange("live")}
            className="px-2.5 py-1.5 rounded-full border border-white/35 text-white text-[13px] cursor-pointer"
            style={{
              background:
                mode === "live" ? "rgba(255,255,255,0.25)" : "transparent",
            }}
          >
            Live System
          </button>
          <div className="px-2.5 py-1.5 rounded-full bg-white/20 text-[13px]">
            v0 MVP
          </div>
        </div>
      </div>
    </div>
  );
}
