// Type definitions for DocTagger API

export interface TaggingResult {
  title: string;
  document_type: string;
  tags: string[];
  summary: string | null;
  date: string | null;
  entities: string[];  // People, organizations, companies mentioned
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
  llm_available: boolean;
  llm_provider: string | null;
  llm_model: string | null;
  // Embedding settings
  embedding_enabled: boolean;
  embedding_model: string | null;
  // Deprecated fields for backward compatibility
  ollama_available?: boolean;
  ollama_model?: string | null;
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
  document_date: string | null;  // Date extracted from document content (YYYY-MM-DD)
  summary: string | null;
  entities: string[];  // People, organizations, companies mentioned
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

export interface BatchUploadResponse {
  batch_id: string;
  files: Array<{
    request_id: string;
    filename: string;
  }>;
  message: string;
}

export interface BatchStatusResponse {
  batch_id: string;
  total: number;
  completed: number;
  failed: number;
  pending: number;
  files: Array<{
    request_id: string;
    filename: string;
    status: ProcessingStatus;
    error?: string;
  }>;
}

export interface CustomPrompt {
  id: string;
  name: string;
  description: string;
  prompt_template: string;
  document_types: string[];
  is_default: boolean;
}

export interface WebSocketMessage {
  type: "status_update" | "completed" | "error" | "batch_progress";
  request_id?: string;
  batch_id?: string;
  status?: string;
  error?: string;
  progress?: {
    completed: number;
    total: number;
  };
  result?: {
    title: string | null;
    document_type: string | null;
    tags: string[];
    archive_path: string | null;
  };
}

// Inbox batch processing types
export type BatchProcessingStatus = 
  | "idle"
  | "running"
  | "paused"
  | "stopping"
  | "completed"
  | "cancelled";

export interface InboxFile {
  name: string;
  path: string;
  size: number;
  modified: string;
  status: "pending" | "already_processed";
}

export interface ProcessedFile {
  name: string;
  status: "success" | "failed" | "skipped";
  error?: string;
  result?: {
    title?: string;
    document_type?: string;
    tags?: string[];
    date?: string;  // Date extracted from document content (YYYY-MM-DD)
    summary?: string;
    entities?: string[];  // People, organizations mentioned
  };
}

export interface BatchProgress {
  status: BatchProcessingStatus;
  total_files: number;
  processed: number;
  skipped: number;
  failed: number;
  current_file: string | null;
  percent_complete: number;
  files_to_process: InboxFile[];
  processed_files: ProcessedFile[];
}
