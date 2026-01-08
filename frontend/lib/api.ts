// API client for DocTagger backend

import type {
  SystemStatus,
  DocumentListItem,
  UploadResponse,
  ProcessingStatusResponse,
  WebSocketMessage,
  BatchUploadResponse,
  BatchStatusResponse,
  CustomPrompt,
  InboxFile,
  BatchProgress,
} from "./types";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export class DocTaggerAPI {
  private baseUrl: string;

  constructor(baseUrl: string = API_BASE_URL) {
    this.baseUrl = baseUrl;
  }

  async getStatus(): Promise<SystemStatus> {
    const response = await fetch(`${this.baseUrl}/api/status`);
    if (!response.ok) {
      throw new Error("Failed to fetch status");
    }
    return response.json();
  }

  async listDocuments(limit: number = 100): Promise<DocumentListItem[]> {
    const response = await fetch(
      `${this.baseUrl}/api/documents?limit=${limit}`
    );
    if (!response.ok) {
      throw new Error("Failed to fetch documents");
    }
    return response.json();
  }

  async uploadFile(file: File): Promise<UploadResponse> {
    const formData = new FormData();
    formData.append("file", file);

    const response = await fetch(`${this.baseUrl}/api/upload`, {
      method: "POST",
      body: formData,
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || "Failed to upload file");
    }

    return response.json();
  }

  async getProcessingStatus(
    requestId: string
  ): Promise<ProcessingStatusResponse> {
    const response = await fetch(
      `${this.baseUrl}/api/process/${requestId}`
    );

    if (!response.ok) {
      if (response.status === 404) {
        throw new Error("Request not found");
      }
      throw new Error("Failed to fetch processing status");
    }

    return response.json();
  }

  async startWatcher(): Promise<{ message: string }> {
    const response = await fetch(`${this.baseUrl}/api/watcher/start`, {
      method: "POST",
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || "Failed to start watcher");
    }

    return response.json();
  }

  async stopWatcher(): Promise<{ message: string }> {
    const response = await fetch(`${this.baseUrl}/api/watcher/stop`, {
      method: "POST",
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || "Failed to stop watcher");
    }

    return response.json();
  }

  async processExisting(skipProcessed: boolean = true): Promise<{
    message: string;
    total: number;
    to_process: number;
    skipped: number;
    skipped_files: string[];
  }> {
    const response = await fetch(
      `${this.baseUrl}/api/watcher/process-existing?skip_processed=${skipProcessed}`,
      {
        method: "POST",
      }
    );

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || "Failed to process existing files");
    }

    return response.json();
  }

  async uploadBatch(files: File[]): Promise<BatchUploadResponse> {
    const formData = new FormData();
    files.forEach((file) => {
      formData.append("files", file);
    });

    const response = await fetch(`${this.baseUrl}/api/batch/upload`, {
      method: "POST",
      body: formData,
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || "Failed to upload batch");
    }

    return response.json();
  }

  async getBatchStatus(batchId: string): Promise<BatchStatusResponse> {
    const response = await fetch(`${this.baseUrl}/api/batch/${batchId}`);

    if (!response.ok) {
      throw new Error("Failed to fetch batch status");
    }

    return response.json();
  }

  // ============ Inbox Batch Processing ============

  async listInboxFiles(): Promise<{
    files: InboxFile[];
    total: number;
    pending: number;
    processed: number;
  }> {
    const response = await fetch(`${this.baseUrl}/api/inbox/files`);
    if (!response.ok) {
      throw new Error("Failed to list inbox files");
    }
    return response.json();
  }

  async getBatchProgress(): Promise<BatchProgress> {
    const response = await fetch(`${this.baseUrl}/api/inbox/batch/progress`);
    if (!response.ok) {
      throw new Error("Failed to get batch progress");
    }
    return response.json();
  }

  async startBatchProcessing(
    skipProcessed: boolean = true,
    forceReprocess: boolean = false
  ): Promise<{
    message: string;
    progress: BatchProgress;
  }> {
    const params = new URLSearchParams({
      skip_processed: String(skipProcessed),
      force_reprocess: String(forceReprocess),
    });
    const response = await fetch(
      `${this.baseUrl}/api/inbox/batch/start?${params}`,
      { method: "POST" }
    );
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || "Failed to start batch processing");
    }
    return response.json();
  }

  async pauseBatchProcessing(): Promise<{
    success: boolean;
    progress: BatchProgress;
  }> {
    const response = await fetch(`${this.baseUrl}/api/inbox/batch/pause`, {
      method: "POST",
    });
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || "Failed to pause batch processing");
    }
    return response.json();
  }

  async resumeBatchProcessing(): Promise<{
    success: boolean;
    progress: BatchProgress;
  }> {
    const response = await fetch(`${this.baseUrl}/api/inbox/batch/resume`, {
      method: "POST",
    });
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || "Failed to resume batch processing");
    }
    return response.json();
  }

  async stopBatchProcessing(): Promise<{
    success: boolean;
    progress: BatchProgress;
  }> {
    const response = await fetch(`${this.baseUrl}/api/inbox/batch/stop`, {
      method: "POST",
    });
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || "Failed to stop batch processing");
    }
    return response.json();
  }

  async getPrompts(): Promise<CustomPrompt[]> {
    const response = await fetch(`${this.baseUrl}/api/prompts`);
    if (!response.ok) {
      throw new Error("Failed to fetch prompts");
    }
    return response.json();
  }

  async createPrompt(prompt: Omit<CustomPrompt, "id">): Promise<CustomPrompt> {
    const response = await fetch(`${this.baseUrl}/api/prompts`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(prompt),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || "Failed to create prompt");
    }

    return response.json();
  }

  async updatePrompt(id: string, prompt: Partial<CustomPrompt>): Promise<CustomPrompt> {
    const response = await fetch(`${this.baseUrl}/api/prompts/${id}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(prompt),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || "Failed to update prompt");
    }

    return response.json();
  }

  async deletePrompt(id: string): Promise<void> {
    const response = await fetch(`${this.baseUrl}/api/prompts/${id}`, {
      method: "DELETE",
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || "Failed to delete prompt");
    }
  }

  /**
   * Get the URL to open/download a document.
   * @param documentPath - Relative path to the document within the archive
   * @returns Full URL to open the document
   */
  getDocumentUrl(documentPath: string): string {
    return `${this.baseUrl}/api/documents/open/${encodeURIComponent(documentPath)}`;
  }

  /**
   * Open a document in a new browser tab.
   * @param documentPath - Relative path to the document within the archive
   */
  openDocument(documentPath: string): void {
    const url = this.getDocumentUrl(documentPath);
    window.open(url, '_blank');
  }

  createWebSocket(
    onMessage: (message: WebSocketMessage) => void,
    onError?: (error: Event) => void
  ): WebSocket {
    const wsUrl = this.baseUrl.replace("http", "ws");
    const ws = new WebSocket(`${wsUrl}/api/ws`);

    ws.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data);
        onMessage(message);
      } catch (error) {
        console.error("Failed to parse WebSocket message:", error);
      }
    };

    ws.onerror = (error) => {
      console.error("WebSocket error:", error);
      if (onError) {
        onError(error);
      }
    };

    return ws;
  }
}

export const api = new DocTaggerAPI();
