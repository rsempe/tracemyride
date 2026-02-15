"use client";

import { useEffect, useState, useCallback } from "react";
import { api, type SavedRoute } from "@/lib/api";
import { useStore } from "@/lib/store";

export function SavedRoutesList() {
  const { savedRoutes, setSavedRoutes, setRoute, setMode, route } = useStore();
  const [showSave, setShowSave] = useState(false);
  const [name, setName] = useState("");
  const [saving, setSaving] = useState(false);

  const loadRoutes = useCallback(async () => {
    try {
      const routes = await api.listRoutes();
      setSavedRoutes(routes);
    } catch {
      // Silently fail on load
    }
  }, [setSavedRoutes]);

  useEffect(() => {
    loadRoutes();
  }, [loadRoutes]);

  const handleSave = async () => {
    if (!route) return;
    setSaving(true);
    try {
      await api.saveRoute({
        name: name || "Unnamed route",
        geojson: {
          type: route.type,
          geometry: route.geometry,
          properties: route.properties,
        },
        distance_km: route.properties.distance_km,
        elevation_gain: route.properties.elevation_gain,
        elevation_loss: route.properties.elevation_loss,
        elevation_profile: route.elevation_profile,
      });
      setShowSave(false);
      setName("");
      await loadRoutes();
    } catch {
      // Error handled silently for MVP
    } finally {
      setSaving(false);
    }
  };

  const handleLoad = async (id: string) => {
    try {
      const detail = await api.getRoute(id);
      setRoute({
        ...detail.geojson,
        elevation_profile: detail.elevation_profile ?? [],
      });
      setMode("viewing");
    } catch {
      // Error handled silently
    }
  };

  const handleDelete = async (id: string) => {
    try {
      await api.deleteRoute(id);
      await loadRoutes();
    } catch {
      // Error handled silently
    }
  };

  return (
    <div className="border-t border-gray-200 dark:border-gray-700 flex-1 flex flex-col min-h-0">
      {/* Save button */}
      {route && (
        <div className="p-4 border-b border-gray-200 dark:border-gray-700">
          {!showSave ? (
            <button
              onClick={() => setShowSave(true)}
              className="w-full py-2 px-4 bg-green-500 hover:bg-green-600 text-white rounded-lg text-sm font-medium transition-colors"
            >
              Save
            </button>
          ) : (
            <div className="space-y-2">
              <input
                type="text"
                placeholder="Route name"
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg text-sm bg-white dark:bg-gray-800 text-gray-900 dark:text-white"
                autoFocus
                onKeyDown={(e) => e.key === "Enter" && handleSave()}
              />
              <div className="flex gap-2">
                <button
                  onClick={handleSave}
                  disabled={saving}
                  className="flex-1 py-2 bg-green-500 hover:bg-green-600 text-white rounded-lg text-sm font-medium transition-colors disabled:opacity-50"
                >
                  {saving ? "..." : "Save"}
                </button>
                <button
                  onClick={() => setShowSave(false)}
                  className="py-2 px-3 bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400 rounded-lg text-sm transition-colors"
                >
                  Cancel
                </button>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Saved routes list */}
      <div className="p-4 overflow-y-auto flex-1">
        <h2 className="text-sm font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide mb-2">
          My routes
        </h2>
        {savedRoutes.length === 0 ? (
          <p className="text-sm text-gray-400 dark:text-gray-500">No saved routes</p>
        ) : (
          <div className="space-y-2">
            {savedRoutes.map((r: SavedRoute) => (
              <div
                key={r.id}
                className="p-3 bg-gray-50 dark:bg-gray-800 rounded-lg group"
              >
                <div className="flex items-start justify-between">
                  <button
                    onClick={() => handleLoad(r.id)}
                    className="text-left flex-1"
                  >
                    <div className="text-sm font-medium text-gray-900 dark:text-white truncate">
                      {r.name}
                    </div>
                    <div className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
                      {r.distance_km} km
                      {r.elevation_gain != null && ` · D+ ${r.elevation_gain}m`}
                    </div>
                  </button>
                  <button
                    onClick={() => handleDelete(r.id)}
                    className="text-gray-400 hover:text-red-500 opacity-0 group-hover:opacity-100 transition-opacity text-xs ml-2 mt-1"
                  >
                    Delete
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
