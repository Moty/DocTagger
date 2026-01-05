// Type definitions for DocTagger API

export interface TaggingResult {
  title: string;
  document_type: string;
  tags: string[];
  summary: string | null;
  date: string | null;
  confidence: number;
}

export interface DocumentMetadata {
  title: string | null;
  author: string | null;
  subject: string | null;
  keywords: string[];
  creator: string;
  producer: string;
}

export enum ProcessingStatus {
  PENDING = "pending",
  PROCESSING = "processing",
  COMPLETED = "completed",
  FAILED = "failed",
  SKIPPED = "skipped",
}

export interface ProcessingResult {
  status: ProcessingStatus;
  original_path: string;
  archive_path: string | null;
  sidecar_path: string | null;
  metadata: DocumentMetadata | null;
  tagging: TaggingResult | null;
  ocr_applied: boolean;
  error: string | null;
  processing_time: number;
  timestamp: string;
}

export interface SystemStatus {
  ollama_available: boolean;
  ollama_model: string | null;
  inbox_folder: string | null;
  archive_folder: string | null;
  watching: boolean;
  processed_count: number;
  failed_count: number;
}

export interface DocumentListItem {
  path: string;
  title: string | null;
  document_type: string | null;
  tags: string[];
  processed_at: string;
  size_bytes: number;
}

export interface UploadResponse {
  request_id: string;
  filename: string;
  message: string;
}

export interface ProcessingStatusResponse {
  request_id: string;
  status: ProcessingStatus;
  result: ProcessingResult | null;
  message: string | null;
}

export interface WebSocketMessage {
  type: "status_update" | "completed" | "error";
  request_id: string;
  status?: string;
  error?: string;
  result?: {
    title: string | null;
    document_type: string | null;
    tags: string[];
    archive_path: string | null;
  };
}
