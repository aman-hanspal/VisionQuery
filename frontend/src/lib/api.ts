import type {
  ClassesResponse,
  LiveDetectRequest,
  LiveDetectResponse,
  QueryRequest,
  QueryResponse,
  UploadResponse,
} from "./types";

const API_BASE = process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";

async function jsonOrThrow<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let msg = `Request failed: ${res.status}`;
    try {
      const data = await res.json();
      msg = data?.detail || msg;
    } catch {
      // ignore
    }
    throw new Error(msg);
  }
  return res.json() as Promise<T>;
}

export function getVideoUrl(videoId: string): string {
  return `${API_BASE}/video/${encodeURIComponent(videoId)}`;
}

export async function uploadVideo(file: File): Promise<UploadResponse> {
  const fd = new FormData();
  fd.append("file", file);
  const res = await fetch(`${API_BASE}/upload`, {
    method: "POST",
    body: fd,
  });
  return jsonOrThrow<UploadResponse>(res);
}

export async function resolveClasses(
  prompt: string,
  options: { signal?: AbortSignal } = {}
): Promise<ClassesResponse> {
  const res = await fetch(`${API_BASE}/classes`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ prompt }),
    signal: options.signal,
  });
  return jsonOrThrow<ClassesResponse>(res);
}

export async function runQuery(req: QueryRequest): Promise<QueryResponse> {
  const res = await fetch(`${API_BASE}/query`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
  });
  return jsonOrThrow<QueryResponse>(res);
}

export async function runLiveDetect(req: LiveDetectRequest): Promise<LiveDetectResponse> {
  const res = await fetch(`${API_BASE}/live/detect`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
  });
  return jsonOrThrow<LiveDetectResponse>(res);
}