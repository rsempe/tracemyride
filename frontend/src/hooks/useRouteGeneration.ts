"use client";

import { useCallback } from "react";
import { api } from "@/lib/api";
import { useStore } from "@/lib/store";

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

  const generate = useCallback(async () => {
    if (!userLocation) {
      setError("Click on the map to place the starting point.");
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
      setError(err instanceof Error ? err.message : "Generation error");
      setMode("idle");
    } finally {
      setLoading(false);
    }
  }, [userLocation, distanceKm, loop, elevationTarget, setRoute, setMode, setLoading, setError]);

  const clear = useCallback(() => {
    setRoute(null);
    setMode("idle");
    setError(null);
  }, [setRoute, setMode, setError]);

  return { generate, clear };
}
