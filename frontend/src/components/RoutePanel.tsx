"use client";

import { useCallback } from "react";
import { useStore } from "@/lib/store";
import { useTranslation } from "@/lib/i18n";
import { useRouteGeneration } from "@/hooks/useRouteGeneration";
import { useRouteDrawing } from "@/hooks/useRouteDrawing";
import { SavedRoutesList } from "@/components/SavedRoutesList";
import type { RouteFeature } from "@/lib/api";

function exportGpx(route: RouteFeature) {
  const pts = route.elevation_profile
    .map((p) => {
      const ele = p.elevation != null ? `<ele>${p.elevation}</ele>` : "";
      return `      <trkpt lat="${p.lat}" lon="${p.lng}">${ele}</trkpt>`;
    })
    .join("\n");

  const gpx = `<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1" creator="TraceMyRide"
     xmlns="http://www.topografix.com/GPX/1/1">
  <metadata>
    <name>TraceMyRide - ${route.properties.distance_km} km</name>
  </metadata>
  <trk>
    <name>${route.properties.distance_km} km - D+${route.properties.elevation_gain}m</name>
    <trkseg>
${pts}
    </trkseg>
  </trk>
</gpx>`;

  const blob = new Blob([gpx], { type: "application/gpx+xml" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `tracemyride-${route.properties.distance_km}km.gpx`;
  a.click();
  URL.revokeObjectURL(url);
}

export function RoutePanel() {
  const {
    mode,
    distanceKm,
    setDistanceKm,
    loop,
    setLoop,
    elevationTarget,
    setElevationTarget,
    route,
    loading,
    error,
    drawingWaypoints,
  } = useStore();

  const { t, locale, setLocale } = useTranslation();
  const { generate, clear } = useRouteGeneration();
  const { startDrawing, finishDrawing, cancelDrawing, undo } = useRouteDrawing();

  return (
    <div className="w-80 h-full bg-white dark:bg-gray-900 border-r border-gray-200 dark:border-gray-700 flex flex-col overflow-y-auto">
      {/* Header */}
      <div className="p-4 border-b border-gray-200 dark:border-gray-700">
        <div className="flex items-center justify-between">
          <h1 className="text-xl font-bold text-gray-900 dark:text-white">TraceMyRide</h1>
          <div className="flex rounded-md overflow-hidden border border-gray-300 dark:border-gray-600 text-xs">
            <button
              onClick={() => setLocale("en")}
              className={`px-2 py-1 font-medium transition-colors ${
                locale === "en"
                  ? "bg-blue-500 text-white"
                  : "bg-white dark:bg-gray-800 text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700"
              }`}
            >
              EN
            </button>
            <button
              onClick={() => setLocale("fr")}
              className={`px-2 py-1 font-medium transition-colors ${
                locale === "fr"
                  ? "bg-blue-500 text-white"
                  : "bg-white dark:bg-gray-800 text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700"
              }`}
            >
              FR
            </button>
          </div>
        </div>
        <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
          {t("appSubtitle")}
        </p>
      </div>

      {/* Generation controls */}
      <div className="p-4 space-y-4">
        {/* Distance slider */}
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
            {t("distance")}: {distanceKm} km
          </label>
          <input
            type="range"
            min={1}
            max={50}
            step={0.5}
            value={distanceKm}
            onChange={(e) => setDistanceKm(parseFloat(e.target.value))}
            className="w-full accent-blue-500"
            disabled={mode === "generating"}
          />
          <div className="flex justify-between text-xs text-gray-400">
            <span>1 km</span>
            <span>50 km</span>
          </div>
        </div>

        {/* Loop toggle */}
        <div className="flex items-center justify-between">
          <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
            {t("loop")}
          </span>
          <button
            onClick={() => setLoop(!loop)}
            disabled={mode === "generating"}
            className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
              loop ? "bg-blue-500" : "bg-gray-300"
            }`}
          >
            <span
              className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                loop ? "translate-x-6" : "translate-x-1"
              }`}
            />
          </button>
        </div>

        {/* Elevation target */}
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
            {t("elevationTarget")}: {elevationTarget ? `${elevationTarget} m` : t("auto")}
          </label>
          <input
            type="range"
            min={0}
            max={2500}
            step={50}
            value={elevationTarget ?? 0}
            onChange={(e) => {
              const v = parseInt(e.target.value);
              setElevationTarget(v === 0 ? null : v);
            }}
            className="w-full accent-blue-500"
            disabled={mode === "generating"}
          />
          <div className="flex justify-between text-xs text-gray-400">
            <span>{t("auto")}</span>
            <span>2500 m</span>
          </div>
        </div>

        {/* Generate button */}
        <button
          onClick={generate}
          disabled={loading || mode === "drawing"}
          className="w-full py-2.5 px-4 bg-blue-500 hover:bg-blue-600 disabled:bg-gray-300 text-white rounded-lg font-medium transition-colors"
        >
          {loading ? t("generating") : t("generateRoute")}
        </button>

        {/* Drawing controls */}
        <div className="flex gap-2">
          {mode !== "drawing" ? (
            <button
              onClick={startDrawing}
              disabled={loading}
              className="flex-1 py-2 px-3 bg-gray-100 hover:bg-gray-200 dark:bg-gray-800 dark:hover:bg-gray-700 text-gray-700 dark:text-gray-300 rounded-lg text-sm font-medium transition-colors"
            >
              {t("draw")}
            </button>
          ) : (
            <>
              <button
                onClick={undo}
                disabled={drawingWaypoints.length === 0}
                className="flex-1 py-2 px-3 bg-gray-100 hover:bg-gray-200 dark:bg-gray-800 text-gray-700 dark:text-gray-300 rounded-lg text-sm transition-colors disabled:opacity-50"
              >
                {t("undo")}
              </button>
              <button
                onClick={finishDrawing}
                disabled={drawingWaypoints.length < 2}
                className="flex-1 py-2 px-3 bg-green-500 hover:bg-green-600 text-white rounded-lg text-sm font-medium transition-colors disabled:opacity-50"
              >
                {t("confirm")}
              </button>
              <button
                onClick={cancelDrawing}
                className="py-2 px-3 bg-red-100 hover:bg-red-200 text-red-600 rounded-lg text-sm transition-colors"
              >
                X
              </button>
            </>
          )}
        </div>

        {/* Clear + Export */}
        {route && mode === "viewing" && (
          <div className="flex gap-2">
            <button
              onClick={clear}
              className="flex-1 py-2 px-4 bg-gray-100 hover:bg-gray-200 dark:bg-gray-800 text-gray-600 dark:text-gray-400 rounded-lg text-sm transition-colors"
            >
              {t("clear")}
            </button>
            <button
              onClick={() => exportGpx(route)}
              className="flex-1 py-2 px-4 bg-green-500 hover:bg-green-600 text-white rounded-lg text-sm font-medium transition-colors"
            >
              {t("exportGpx")}
            </button>
          </div>
        )}

        {/* Error */}
        {error && (
          <div className="p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg text-sm text-red-600 dark:text-red-400">
            {error}
          </div>
        )}

        {/* Route stats */}
        {route && (
          <div className="p-3 bg-blue-50 dark:bg-blue-900/20 rounded-lg space-y-1">
            <div className="text-sm font-medium text-blue-900 dark:text-blue-200">
              {route.properties.distance_km} km
            </div>
            <div className="text-xs text-blue-700 dark:text-blue-300">
              D+ {route.properties.elevation_gain} m / D- {route.properties.elevation_loss} m
            </div>
          </div>
        )}
      </div>

      {/* Saved routes */}
      <SavedRoutesList />
    </div>
  );
}
