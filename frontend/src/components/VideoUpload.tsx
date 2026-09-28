"use client";

interface VideoUploadProps {
  onUpload: (file: File) => Promise<void>;
  busy: boolean;
  videoId: string;
}

export default function VideoUpload({
  onUpload,
  busy,
  videoId,
}: VideoUploadProps) {
  return (
    <div className="card">
      <div className="font-bold mb-2">Upload</div>
      <div className="flex gap-2 items-center flex-wrap">
        <input
          type="file"
          accept="video/*"
          onChange={(e) => {
            const f = e.target.files?.[0];
            if (f) void onUpload(f);
            e.target.value = "";
          }}
          disabled={busy}
          className="input-field"
        />
        {videoId && (
          <span className="text-slate-600 text-[13px]">
            video_id: <code>{videoId}</code>
          </span>
        )}
      </div>
    </div>
  );
}
