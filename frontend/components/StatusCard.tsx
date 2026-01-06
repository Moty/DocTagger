"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { SystemStatus } from "@/lib/types";

export function StatusCard() {
  const [status, setStatus] = useState<SystemStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadStatus();
    const interval = setInterval(loadStatus, 5000); // Refresh every 5 seconds
    return () => clearInterval(interval);
  }, []);

  const loadStatus = async () => {
    try {
      const data = await api.getStatus();
      setStatus(data);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load status");
    } finally {
      setLoading(false);
    }
  };

  const handleStartWatcher = async () => {
    try {
      await api.startWatcher();
      await loadStatus();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to start watcher");
    }
  };

  const handleStopWatcher = async () => {
    try {
      await api.stopWatcher();
      await loadStatus();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to stop watcher");
    }
  };

  if (loading) {
    return (
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6">
        <div className="animate-pulse">
          <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-1/4 mb-4"></div>
          <div className="space-y-3">
            <div className="h-3 bg-gray-200 dark:bg-gray-700 rounded"></div>
            <div className="h-3 bg-gray-200 dark:bg-gray-700 rounded w-5/6"></div>
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 dark:bg-red-900/20 rounded-lg shadow-md p-6">
        <h2 className="text-xl font-semibold text-red-800 dark:text-red-200 mb-2">
          Error
        </h2>
        <p className="text-red-600 dark:text-red-400">{error}</p>
      </div>
    );
  }

  if (!status) return null;

  const llmAvailable = status.llm_available ?? status.ollama_available;
  const llmProvider = status.llm_provider ?? "ollama";
  const llmModel = status.llm_model ?? status.ollama_model;

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6">
      <h2 className="text-2xl font-bold mb-4 text-gray-800 dark:text-white">
        System Status
      </h2>

      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <span className="text-gray-600 dark:text-gray-300">LLM ({llmProvider}):</span>
          <span
            className={`px-3 py-1 rounded-full text-sm font-medium ${
              llmAvailable
                ? "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200"
                : "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200"
            }`}
          >
            {llmAvailable ? "Available" : "Unavailable"}
          </span>
        </div>

        {llmModel && (
          <div className="flex items-center justify-between">
            <span className="text-gray-600 dark:text-gray-300">Model:</span>
            <span className="text-gray-800 dark:text-white font-mono text-sm truncate max-w-[180px]" title={llmModel}>
              {llmModel}
            </span>
          </div>
        )}

        <div className="flex items-center justify-between">
          <span className="text-gray-600 dark:text-gray-300">Watcher:</span>
          <span
            className={`px-3 py-1 rounded-full text-sm font-medium ${
              status.watching
                ? "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200"
                : "bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-200"
            }`}
          >
            {status.watching ? "Running" : "Stopped"}
          </span>
        </div>

        <div className="flex items-center justify-between">
          <span className="text-gray-600 dark:text-gray-300">Processed:</span>
          <span className="text-gray-800 dark:text-white font-semibold">
            {status.processed_count}
          </span>
        </div>

        <div className="flex items-center justify-between">
          <span className="text-gray-600 dark:text-gray-300">Failed:</span>
          <span className="text-gray-800 dark:text-white font-semibold">
            {status.failed_count}
          </span>
        </div>

        <div className="border-t dark:border-gray-700 pt-3 mt-3">
          <div className="text-xs text-gray-500 dark:text-gray-400 space-y-1">
            <div>Inbox: {status.inbox_folder}</div>
            <div>Archive: {status.archive_folder}</div>
          </div>
        </div>

        <div className="flex gap-2 pt-3">
          {!status.watching ? (
            <button
              onClick={handleStartWatcher}
              className="flex-1 bg-green-600 hover:bg-green-700 text-white px-4 py-2 rounded-md font-medium transition-colors"
            >
              Start Watcher
            </button>
          ) : (
            <button
              onClick={handleStopWatcher}
              className="flex-1 bg-red-600 hover:bg-red-700 text-white px-4 py-2 rounded-md font-medium transition-colors"
            >
              Stop Watcher
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
