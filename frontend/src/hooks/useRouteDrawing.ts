"use client";

import { useCallback } from "react";
import { api } from "@/lib/api";
import { useStore } from "@/lib/store";

export function useRouteDrawing() {
  const {
    setMode,
    setRoute,
    setLoading,
    setError,
    clearWaypoints,
    undoWaypoint,
    drawingWaypoints,
  } = useStore();

  const startDrawing = useCallback(() => {
    setRoute(null);
    clearWaypoints();
    setError(null);
    setMode("drawing");
  }, [setRoute, clearWaypoints, setError, setMode]);

  const finishDrawing = useCallback(async () => {
    if (drawingWaypoints.length < 2) {
      setError("Placez au moins 2 points sur la carte.");
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const result = await api.snap(drawingWaypoints);
      setRoute(result);
      clearWaypoints();
      setMode("viewing");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erreur de snap-to-road");
    } finally {
      setLoading(false);
    }
  }, [drawingWaypoints, setLoading, setError, setRoute, clearWaypoints, setMode]);

  const cancelDrawing = useCallback(() => {
    clearWaypoints();
    setMode("idle");
    setError(null);
  }, [clearWaypoints, setMode, setError]);

  const undo = useCallback(() => {
    undoWaypoint();
  }, [undoWaypoint]);

  return { startDrawing, finishDrawing, cancelDrawing, undo };
}
