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
  }
  
  export interface LiveDetectRequest {
    image_b64: string;
    prompt?: string;
    classes?: string[];
    conf?: number;
  }
  
  export interface QueryResponse {
    detections: Detection[];
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