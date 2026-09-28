export interface Detection {
  label: string;
  conf: number;
  bbox: number[];
  t?: number;
}

export interface QueryRequest {
  video_id: string;
  prompt?: string;
  classes?: string[];
  fps?: number;
  conf?: number;
  scan_mode?: "full" | "budget";
  frame_budget?: number;
  max_sampled_frames?: number;
}

export interface LiveDetectRequest {
  image_b64: string;
  prompt?: string;
  classes?: string[];
  conf?: number;
}

export interface ScanMetadata {
  scan_mode: "full" | "budget";
  scan_complete: boolean;
  stop_reason: string;
  detector_calls: number;
  frames_read: number;
  effective_sample_fps: number;
  selected_timestamps: number[];
  elapsed_seconds: number;
  detections_truncated: boolean;
  total_detections: number;
  dropped_detections: number;
  run_id: string;
  run_log_saved: boolean;
}

export interface QueryResponse {
  detections: Detection[];
  classes: string[];
  metadata: ScanMetadata;
}
export interface ClassesResponse {
  classes: string[];
}
export interface LiveDetectResponse {
  detections: Detection[];
  frame_width: number;
  frame_height: number;
  classes: string[];
}
export interface UploadResponse {
  video_id: string;
}
