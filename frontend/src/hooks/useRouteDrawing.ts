"use client";

import { useCallback } from "react";
import { api } from "@/lib/api";
import { useStore } from "@/lib/store";
import { useTranslation } from "@/lib/i18n";

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

  const { t } = useTranslation();

  const startDrawing = useCallback(() => {
    setRoute(null);
    clearWaypoints();
    setError(null);
    setMode("drawing");
  }, [setRoute, clearWaypoints, setError, setMode]);

  const finishDrawing = useCallback(async () => {
    if (drawingWaypoints.length < 2) {
      setError(t("drawMinPoints"));
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
      setError(err instanceof Error ? err.message : t("snapError"));
    } finally {
      setLoading(false);
    }
  }, [drawingWaypoints, setLoading, setError, setRoute, clearWaypoints, setMode, t]);

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
