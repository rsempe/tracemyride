"use client";

import { useCallback } from "react";
import { api } from "@/lib/api";
import { useStore } from "@/lib/store";
import { useTranslation } from "@/lib/i18n";

export function useExplorer() {
  const {
    userLocation,
    explorerRadius,
    explorerRouteTypes,
    setExplorerRoutes,
    setSelectedExplorerId,
    setMode,
    setLoading,
    setError,
  } = useStore();

  const { t } = useTranslation();

  const explore = useCallback(async () => {
    if (!userLocation) {
      setError(t("clickToPlaceStart"));
      return;
    }

    setLoading(true);
    setError(null);
    setMode("exploring");

    try {
      const result = await api.explore({
        lat: userLocation[1],
        lng: userLocation[0],
        radius_km: explorerRadius,
        route_types: explorerRouteTypes,
      });
      setExplorerRoutes(result.routes);
    } catch (err) {
      setError(err instanceof Error ? err.message : t("explorerError"));
    } finally {
      setLoading(false);
    }
  }, [userLocation, explorerRadius, explorerRouteTypes, setExplorerRoutes, setMode, setLoading, setError, t]);

  const selectRoute = useCallback(
    (osmId: number) => {
      setSelectedExplorerId(osmId);
    },
    [setSelectedExplorerId]
  );

  const exitExplorer = useCallback(() => {
    setExplorerRoutes([]);
    setSelectedExplorerId(null);
    setError(null);
    setMode("idle");
  }, [setExplorerRoutes, setSelectedExplorerId, setError, setMode]);

  return { explore, selectRoute, exitExplorer };
}
