"use client";

import { useCallback } from "react";
import { api } from "@/lib/api";
import { useStore } from "@/lib/store";
import { useTranslation } from "@/lib/i18n";

export function useRouteGeneration() {
  const {
    distanceKm,
    loop,
    elevationTarget,
    userLocation,
    setRoute,
    setMode,
    setLoading,
    setError,
  } = useStore();

  const { t } = useTranslation();

  const generate = useCallback(async () => {
    if (!userLocation) {
      setError(t("clickToPlaceStart"));
      return;
    }

    setLoading(true);
    setError(null);
    setMode("generating");

    try {
      const result = await api.generate({
        lat: userLocation[1],
        lng: userLocation[0],
        distance_km: distanceKm,
        loop,
        elevation_target: elevationTarget ?? undefined,
      });
      setRoute(result);
      setMode("viewing");
    } catch (err) {
      setError(err instanceof Error ? err.message : t("generationError"));
      setMode("idle");
    } finally {
      setLoading(false);
    }
  }, [userLocation, distanceKm, loop, elevationTarget, setRoute, setMode, setLoading, setError, t]);

  const clear = useCallback(() => {
    setRoute(null);
    setMode("idle");
    setError(null);
  }, [setRoute, setMode, setError]);

  return { generate, clear };
}
