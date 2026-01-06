// Custom React hooks for DocTagger

import { useEffect, useRef, useState, useCallback } from "react";
import { api } from "./api";
import type { WebSocketMessage, SystemStatus } from "./types";

/**
 * Hook for WebSocket connection with auto-reconnect
 */
export function useWebSocket(onMessage: (message: WebSocketMessage) => void) {
  const [connected, setConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    try {
      wsRef.current = api.createWebSocket(
        (message) => {
          onMessage(message);
        },
        () => {
          setError("WebSocket connection error");
          setConnected(false);
          // Auto-reconnect after 5 seconds
          reconnectTimeoutRef.current = setTimeout(connect, 5000);
        }
      );

      wsRef.current.onopen = () => {
        setConnected(true);
        setError(null);
      };

      wsRef.current.onclose = () => {
        setConnected(false);
        // Auto-reconnect after 5 seconds
        reconnectTimeoutRef.current = setTimeout(connect, 5000);
      };
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to connect");
    }
  }, [onMessage]);

  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
    }
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
    setConnected(false);
  }, []);

  useEffect(() => {
    connect();
    return () => disconnect();
  }, [connect, disconnect]);

  return { connected, error, reconnect: connect, disconnect };
}

/**
 * Hook for polling system status
 */
export function useSystemStatus(intervalMs: number = 5000) {
  const [status, setStatus] = useState<SystemStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      const data = await api.getStatus();
      setStatus(data);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load status");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
    const interval = setInterval(refresh, intervalMs);
    return () => clearInterval(interval);
  }, [refresh, intervalMs]);

  return { status, loading, error, refresh };
}

/**
 * Hook for tracking file processing progress
 */
export function useProcessingTracker() {
  const [processing, setProcessing] = useState<Map<string, {
    filename: string;
    status: string;
    progress?: number;
    error?: string;
  }>>(new Map());

  const addFile = useCallback((requestId: string, filename: string) => {
    setProcessing((prev) => {
      const next = new Map(prev);
      next.set(requestId, { filename, status: "pending" });
      return next;
    });
  }, []);

  const updateStatus = useCallback((requestId: string, status: string, error?: string) => {
    setProcessing((prev) => {
      const next = new Map(prev);
      const existing = next.get(requestId);
      if (existing) {
        next.set(requestId, { ...existing, status, error });
      }
      return next;
    });
  }, []);

  const removeFile = useCallback((requestId: string) => {
    setProcessing((prev) => {
      const next = new Map(prev);
      next.delete(requestId);
      return next;
    });
  }, []);

  const clearCompleted = useCallback(() => {
    setProcessing((prev) => {
      const next = new Map(prev);
      for (const [id, item] of next) {
        if (item.status === "completed" || item.status === "failed") {
          next.delete(id);
        }
      }
      return next;
    });
  }, []);

  return {
    processing,
    addFile,
    updateStatus,
    removeFile,
    clearCompleted,
    hasActiveProcessing: Array.from(processing.values()).some(
      (p) => p.status === "pending" || p.status === "processing"
    ),
  };
}
