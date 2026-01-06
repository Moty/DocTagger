"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { api } from "@/lib/api";
import type { BatchProgress, InboxFile } from "@/lib/types";

export function BatchProcessingPanel() {
  const [progress, setProgress] = useState<BatchProgress | null>(null);
  const [files, setFiles] = useState<InboxFile[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<"pending" | "processed">("pending");
  
  // Use ref to track if we should be polling
  const isPollingRef = useRef(false);

  // Fetch initial data
  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      const [progressData, filesData] = await Promise.all([
        api.getBatchProgress(),
        api.listInboxFiles(),
      ]);
      setProgress(progressData);
      setFiles(filesData.files);
      setError(null);
      
      // Update polling ref based on status
      isPollingRef.current = progressData.status === "running" || progressData.status === "paused" || progressData.status === "stopping";
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to fetch data");
    } finally {
      setLoading(false);
    }
  }, []);

  // Poll for updates when processing is active
  useEffect(() => {
    fetchData();

    const interval = setInterval(async () => {
      // Always poll to catch status changes
      try {
        const progressData = await api.getBatchProgress();
        setProgress(progressData);
        
        // Update polling status
        const shouldPoll = progressData.status === "running" || progressData.status === "paused" || progressData.status === "stopping";
        isPollingRef.current = shouldPoll;
        
        // If completed or cancelled, also refresh file list
        if (progressData.status === "completed" || progressData.status === "cancelled") {
          const filesData = await api.listInboxFiles();
          setFiles(filesData.files);
        }
      } catch (err) {
        console.error("Polling error:", err);
      }
    }, 1000);

    return () => clearInterval(interval);
  }, [fetchData]);

  const handleStart = async () => {
    try {
      setError(null);
      const result = await api.startBatchProcessing(true);
      setProgress(result.progress);
      isPollingRef.current = true;
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to start");
    }
  };

  const handlePause = async () => {
    try {
      const result = await api.pauseBatchProcessing();
      setProgress(result.progress);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to pause");
    }
  };

  const handleResume = async () => {
    try {
      const result = await api.resumeBatchProcessing();
      setProgress(result.progress);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to resume");
    }
  };

  const handleStop = async () => {
    try {
      const result = await api.stopBatchProcessing();
      setProgress(result.progress);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to stop");
    }
  };

  const handleRefresh = () => {
    fetchData();
  };

  const isRunning = progress?.status === "running";
  const isPaused = progress?.status === "paused";
  const isIdle = !progress || progress.status === "idle" || progress.status === "completed" || progress.status === "cancelled";

  const pendingFiles = files.filter(f => f.status === "pending");
  const processedFiles = progress?.processed_files || [];

  return (
    <div className="bg-white rounded-lg shadow-md p-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-semibold text-gray-800">
          Inbox Batch Processing
        </h2>
        <button
          onClick={handleRefresh}
          disabled={loading}
          className="text-gray-500 hover:text-gray-700 disabled:opacity-50"
          title="Refresh"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
          </svg>
        </button>
      </div>

      {error && (
        <div className="mb-4 p-3 bg-red-100 border border-red-300 text-red-700 rounded">
          {error}
        </div>
      )}

      {/* Progress Section */}
      {progress && (progress.status === "running" || progress.status === "paused" || progress.status === "stopping") && (
        <div className="mb-6 p-4 bg-blue-50 rounded-lg">
          <div className="flex items-center justify-between mb-2">
            <span className="font-medium text-blue-800">
              {progress.status === "running" && "Processing..."}
              {progress.status === "paused" && "Paused"}
              {progress.status === "stopping" && "Stopping..."}
            </span>
            <span className="text-sm text-blue-600">
              {progress.processed + progress.skipped + progress.failed} / {progress.total_files}
            </span>
          </div>

          {/* Progress Bar */}
          <div className="w-full bg-blue-200 rounded-full h-3 mb-3">
            <div
              className="bg-blue-600 h-3 rounded-full transition-all duration-300"
              style={{ width: `${progress.percent_complete}%` }}
            />
          </div>

          {/* Current File */}
          {progress.current_file && (
            <p className="text-sm text-blue-700 mb-3 truncate">
              Current: {progress.current_file}
            </p>
          )}

          {/* Stats */}
          <div className="grid grid-cols-3 gap-4 text-center text-sm">
            <div className="bg-green-100 rounded p-2">
              <div className="text-green-800 font-semibold">{progress.processed}</div>
              <div className="text-green-600">Processed</div>
            </div>
            <div className="bg-yellow-100 rounded p-2">
              <div className="text-yellow-800 font-semibold">{progress.skipped}</div>
              <div className="text-yellow-600">Skipped</div>
            </div>
            <div className="bg-red-100 rounded p-2">
              <div className="text-red-800 font-semibold">{progress.failed}</div>
              <div className="text-red-600">Failed</div>
            </div>
          </div>
        </div>
      )}

      {/* Completed/Cancelled Summary */}
      {progress && (progress.status === "completed" || progress.status === "cancelled") && (
        <div className="mb-6 p-4 bg-gray-50 rounded-lg">
          <div className="flex items-center gap-2 mb-2">
            {progress.status === "completed" ? (
              <svg className="w-5 h-5 text-green-500" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
              </svg>
            ) : (
              <svg className="w-5 h-5 text-yellow-500" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
              </svg>
            )}
            <span className="font-medium">
              {progress.status === "completed" ? "Processing Complete" : "Processing Cancelled"}
            </span>
          </div>
          <p className="text-sm text-gray-600">
            Processed: {progress.processed} | Skipped: {progress.skipped} | Failed: {progress.failed}
          </p>
        </div>
      )}

      {/* Control Buttons */}
      <div className="flex gap-3 mb-6">
        {isIdle && (
          <button
            onClick={handleStart}
            disabled={pendingFiles.length === 0}
            className="flex-1 bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            Start Processing ({pendingFiles.length} files)
          </button>
        )}
        
        {isRunning && (
          <>
            <button
              onClick={handlePause}
              className="flex-1 bg-yellow-500 text-white px-4 py-2 rounded-lg hover:bg-yellow-600 transition-colors"
            >
              Pause
            </button>
            <button
              onClick={handleStop}
              className="flex-1 bg-red-500 text-white px-4 py-2 rounded-lg hover:bg-red-600 transition-colors"
            >
              Stop
            </button>
          </>
        )}

        {isPaused && (
          <>
            <button
              onClick={handleResume}
              className="flex-1 bg-green-500 text-white px-4 py-2 rounded-lg hover:bg-green-600 transition-colors"
            >
              Resume
            </button>
            <button
              onClick={handleStop}
              className="flex-1 bg-red-500 text-white px-4 py-2 rounded-lg hover:bg-red-600 transition-colors"
            >
              Stop
            </button>
          </>
        )}
      </div>

      {/* Tab Navigation */}
      <div className="flex border-b border-gray-200 mb-4">
        <button
          onClick={() => setActiveTab("pending")}
          className={`px-4 py-2 font-medium text-sm ${
            activeTab === "pending"
              ? "text-blue-600 border-b-2 border-blue-600"
              : "text-gray-500 hover:text-gray-700"
          }`}
        >
          Pending ({pendingFiles.length})
        </button>
        <button
          onClick={() => setActiveTab("processed")}
          className={`px-4 py-2 font-medium text-sm ${
            activeTab === "processed"
              ? "text-blue-600 border-b-2 border-blue-600"
              : "text-gray-500 hover:text-gray-700"
          }`}
        >
          Processed ({processedFiles.length})
        </button>
      </div>

      {/* File Lists */}
      <div className="max-h-80 overflow-y-auto">
        {activeTab === "pending" && (
          <div className="space-y-2">
            {pendingFiles.length === 0 ? (
              <p className="text-gray-500 text-center py-4">No pending files</p>
            ) : (
              pendingFiles.map((file, index) => (
                <div
                  key={index}
                  className="flex items-center justify-between p-3 bg-gray-50 rounded hover:bg-gray-100"
                >
                  <div className="flex items-center gap-2 min-w-0">
                    <svg className="w-5 h-5 text-gray-400 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4z" clipRule="evenodd" />
                    </svg>
                    <span className="text-sm text-gray-700 truncate">{file.name}</span>
                  </div>
                  <span className="text-xs text-gray-500 flex-shrink-0 ml-2">
                    {formatFileSize(file.size)}
                  </span>
                </div>
              ))
            )}
          </div>
        )}

        {activeTab === "processed" && (
          <div className="space-y-2">
            {processedFiles.length === 0 ? (
              <p className="text-gray-500 text-center py-4">No processed files yet</p>
            ) : (
              processedFiles.map((file, index) => (
                <div
                  key={index}
                  className={`p-3 rounded ${
                    file.status === "success"
                      ? "bg-green-50"
                      : file.status === "failed"
                      ? "bg-red-50"
                      : "bg-yellow-50"
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2 min-w-0">
                      {file.status === "success" && (
                        <svg className="w-5 h-5 text-green-500 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                          <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                        </svg>
                      )}
                      {file.status === "failed" && (
                        <svg className="w-5 h-5 text-red-500 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                          <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                        </svg>
                      )}
                      {file.status === "skipped" && (
                        <svg className="w-5 h-5 text-yellow-500 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                          <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-12a1 1 0 10-2 0v4a1 1 0 00.293.707l2.828 2.829a1 1 0 101.415-1.415L11 9.586V6z" clipRule="evenodd" />
                        </svg>
                      )}
                      <span className="text-sm text-gray-700 truncate">{file.name}</span>
                    </div>
                    <span
                      className={`text-xs px-2 py-1 rounded flex-shrink-0 ml-2 ${
                        file.status === "success"
                          ? "bg-green-200 text-green-800"
                          : file.status === "failed"
                          ? "bg-red-200 text-red-800"
                          : "bg-yellow-200 text-yellow-800"
                      }`}
                    >
                      {file.status}
                    </span>
                  </div>
                  {file.error && (
                    <p className="text-xs text-red-600 mt-1 pl-7">{file.error}</p>
                  )}
                  {file.result?.document_type && (
                    <p className="text-xs text-gray-600 mt-1 pl-7">
                      Type: {file.result.document_type}
                    </p>
                  )}
                </div>
              ))
            )}
          </div>
        )}
      </div>
    </div>
  );
}

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}
