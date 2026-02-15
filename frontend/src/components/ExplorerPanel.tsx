"use client";

import { useStore } from "@/lib/store";
import { useTranslation } from "@/lib/i18n";
import { useExplorer } from "@/hooks/useExplorer";

const ROUTE_TYPE_COLORS: Record<string, string> = {
  hiking: "#e74c3c",
  foot: "#e67e22",
  bicycle: "#2ecc71",
  mtb: "#8e44ad",
  running: "#3498db",
};

const ROUTE_TYPE_KEYS: { type: string; labelKey: "hiking" | "foot" | "cycling" | "mountainBike" | "running" }[] = [
  { type: "hiking", labelKey: "hiking" },
  { type: "foot", labelKey: "foot" },
  { type: "bicycle", labelKey: "cycling" },
  { type: "mtb", labelKey: "mountainBike" },
  { type: "running", labelKey: "running" },
];

export function ExplorerPanel() {
  const {
    explorerRoutes,
    selectedExplorerId,
    explorerRadius,
    setExplorerRadius,
    explorerRouteTypes,
    setExplorerRouteTypes,
    loading,
    error,
  } = useStore();

  const { t } = useTranslation();
  const { explore, selectRoute, exitExplorer } = useExplorer();

  const toggleRouteType = (type: string) => {
    if (explorerRouteTypes.includes(type)) {
      if (explorerRouteTypes.length > 1) {
        setExplorerRouteTypes(explorerRouteTypes.filter((t) => t !== type));
      }
    } else {
      setExplorerRouteTypes([...explorerRouteTypes, type]);
    }
  };

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="p-4 border-b border-gray-200 dark:border-gray-700">
        <div className="flex items-center gap-2">
          <button
            onClick={exitExplorer}
            className="p-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-600 dark:text-gray-400 transition-colors"
          >
            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M19 12H5M12 19l-7-7 7-7" />
            </svg>
          </button>
          <div>
            <h2 className="text-lg font-bold text-gray-900 dark:text-white">{t("explore")}</h2>
            <p className="text-xs text-gray-500 dark:text-gray-400">{t("explorerSubtitle")}</p>
          </div>
        </div>
      </div>

      {/* Controls */}
      <div className="p-4 space-y-4 border-b border-gray-200 dark:border-gray-700">
        {/* Radius slider */}
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
            {t("searchRadius")}: {explorerRadius} km
          </label>
          <input
            type="range"
            min={1}
            max={20}
            step={1}
            value={explorerRadius}
            onChange={(e) => setExplorerRadius(parseInt(e.target.value))}
            className="w-full accent-amber-500"
            disabled={loading}
          />
          <div className="flex justify-between text-xs text-gray-400">
            <span>1 km</span>
            <span>20 km</span>
          </div>
        </div>

        {/* Route type toggles */}
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
            {t("routeTypes")}
          </label>
          <div className="flex flex-wrap gap-2">
            {ROUTE_TYPE_KEYS.map(({ type, labelKey }) => {
              const active = explorerRouteTypes.includes(type);
              const color = ROUTE_TYPE_COLORS[type];
              return (
                <button
                  key={type}
                  onClick={() => toggleRouteType(type)}
                  disabled={loading}
                  className="px-3 py-1.5 rounded-full text-xs font-medium transition-all border"
                  style={{
                    backgroundColor: active ? color : "transparent",
                    borderColor: color,
                    color: active ? "white" : color,
                    opacity: loading ? 0.5 : 1,
                  }}
                >
                  {t(labelKey)}
                </button>
              );
            })}
          </div>
        </div>

        {/* Search button */}
        <button
          onClick={explore}
          disabled={loading}
          className="w-full py-2.5 px-4 bg-amber-500 hover:bg-amber-600 disabled:bg-gray-300 text-white rounded-lg font-medium transition-colors"
        >
          {loading ? t("searching") : t("searchRoutes")}
        </button>
      </div>

      {/* Error */}
      {error && (
        <div className="mx-4 mt-3 p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg text-sm text-red-600 dark:text-red-400">
          {error}
        </div>
      )}

      {/* Results */}
      <div className="flex-1 overflow-y-auto p-4">
        {explorerRoutes.length > 0 && (
          <p className="text-sm text-gray-500 dark:text-gray-400 mb-3">
            {explorerRoutes.length} {t("routesFound")}
          </p>
        )}

        {!loading && explorerRoutes.length === 0 && (
          <p className="text-sm text-gray-400 dark:text-gray-500 text-center mt-4">
            {t("noExplorerResults")}
          </p>
        )}

        <div className="space-y-2">
          {explorerRoutes.map((route) => {
            const isSelected = selectedExplorerId === route.osm_id;
            const color = ROUTE_TYPE_COLORS[route.route_type] || "#888";
            return (
              <button
                key={route.osm_id}
                onClick={() => selectRoute(route.osm_id)}
                className={`w-full text-left p-3 rounded-lg border transition-all ${
                  isSelected
                    ? "border-2 shadow-sm"
                    : "border-gray-200 dark:border-gray-700 hover:border-gray-300 dark:hover:border-gray-600"
                }`}
                style={isSelected ? { borderColor: color, backgroundColor: `${color}10` } : {}}
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span
                        className="inline-block w-2.5 h-2.5 rounded-full flex-shrink-0"
                        style={{ backgroundColor: color }}
                      />
                      <span className="text-sm font-medium text-gray-900 dark:text-white truncate">
                        {route.name || route.ref || `Route #${route.osm_id}`}
                      </span>
                    </div>
                    <div className="flex items-center gap-3 mt-1 ml-4.5">
                      {route.ref && route.name && (
                        <span className="text-xs text-gray-500 dark:text-gray-400">{route.ref}</span>
                      )}
                      {route.network && (
                        <span className="text-xs text-gray-400 dark:text-gray-500">{route.network}</span>
                      )}
                    </div>
                  </div>
                  {route.distance != null && (
                    <span className="text-xs font-medium text-gray-500 dark:text-gray-400 whitespace-nowrap">
                      {route.distance} km
                    </span>
                  )}
                </div>
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );
}
