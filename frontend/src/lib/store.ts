import { create } from "zustand";
import type { RouteFeature, SavedRoute } from "./api";

export type AppMode = "idle" | "generating" | "drawing" | "viewing";

interface RouteState {
  // App mode
  mode: AppMode;
  setMode: (mode: AppMode) => void;

  // Generation params
  distanceKm: number;
  setDistanceKm: (d: number) => void;
  loop: boolean;
  setLoop: (l: boolean) => void;
  elevationTarget: number | null;
  setElevationTarget: (e: number | null) => void;

  // Current route
  route: RouteFeature | null;
  setRoute: (r: RouteFeature | null) => void;

  // Drawing waypoints
  drawingWaypoints: number[][];
  addWaypoint: (coord: number[]) => void;
  undoWaypoint: () => void;
  clearWaypoints: () => void;

  // Saved routes
  savedRoutes: SavedRoute[];
  setSavedRoutes: (routes: SavedRoute[]) => void;

  // User location
  userLocation: [number, number] | null;
  setUserLocation: (loc: [number, number] | null) => void;

  // Hovered point on elevation profile (for map sync)
  hoveredRoutePoint: [number, number] | null;
  setHoveredRoutePoint: (p: [number, number] | null) => void;

  // Loading / error
  loading: boolean;
  setLoading: (l: boolean) => void;
  error: string | null;
  setError: (e: string | null) => void;
}

export const useStore = create<RouteState>((set) => ({
  mode: "idle",
  setMode: (mode) => set({ mode }),

  distanceKm: 5,
  setDistanceKm: (distanceKm) => set({ distanceKm }),
  loop: true,
  setLoop: (loop) => set({ loop }),
  elevationTarget: null,
  setElevationTarget: (elevationTarget) => set({ elevationTarget }),

  route: null,
  setRoute: (route) => set({ route }),

  drawingWaypoints: [],
  addWaypoint: (coord) =>
    set((s) => ({ drawingWaypoints: [...s.drawingWaypoints, coord] })),
  undoWaypoint: () =>
    set((s) => ({ drawingWaypoints: s.drawingWaypoints.slice(0, -1) })),
  clearWaypoints: () => set({ drawingWaypoints: [] }),

  savedRoutes: [],
  setSavedRoutes: (savedRoutes) => set({ savedRoutes }),

  userLocation: null,
  setUserLocation: (userLocation) => set({ userLocation }),

  hoveredRoutePoint: null,
  setHoveredRoutePoint: (hoveredRoutePoint) => set({ hoveredRoutePoint }),

  loading: false,
  setLoading: (loading) => set({ loading }),
  error: null,
  setError: (error) => set({ error }),
}));
