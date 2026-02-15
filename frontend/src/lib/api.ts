const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(error.detail || "API error");
  }
  return res.json();
}

export interface GenerateParams {
  lat: number;
  lng: number;
  distance_km: number;
  loop: boolean;
  elevation_target?: number;
  prefer_trails?: boolean;
}

export interface RouteFeature {
  type: "Feature";
  geometry: { type: "LineString"; coordinates: number[][] };
  properties: {
    distance_km: number;
    elevation_gain: number;
    elevation_loss: number;
  };
  elevation_profile: { distance_km: number; elevation: number | null; lat: number; lng: number }[];
}

export interface SavedRoute {
  id: string;
  name: string;
  distance_km: number;
  elevation_gain: number | null;
  elevation_loss: number | null;
  created_at: string;
}

export interface SavedRouteDetail extends SavedRoute {
  geojson: RouteFeature;
  elevation_profile: { distance_km: number; elevation: number | null }[] | null;
}

export interface ExploredRouteData {
  osm_id: number;
  name: string | null;
  ref: string | null;
  route_type: string;
  network: string | null;
  distance: number | null;
  geojson: {
    type: "Feature";
    geometry: { type: string; coordinates: number[][] | number[][][] };
    properties: Record<string, unknown>;
  };
}

export interface ExploreParams {
  lat: number;
  lng: number;
  radius_km: number;
  route_types: string[];
}

export interface ExploreResponse {
  routes: ExploredRouteData[];
  query_center: { lat: number; lng: number };
  query_radius_km: number;
}

export const api = {
  generate: (params: GenerateParams) =>
    request<RouteFeature>("/api/v1/generate", {
      method: "POST",
      body: JSON.stringify(params),
    }),

  elevationProfile: (coordinates: number[][]) =>
    request<{
      profile: { distance_km: number; elevation: number | null }[];
      elevation_gain: number;
      elevation_loss: number;
    }>("/api/v1/elevation/profile", {
      method: "POST",
      body: JSON.stringify({ coordinates }),
    }),

  snap: (coordinates: number[][]) =>
    request<RouteFeature>("/api/v1/snap", {
      method: "POST",
      body: JSON.stringify({ coordinates }),
    }),

  saveRoute: (data: {
    name: string;
    geojson: object;
    distance_km: number;
    elevation_gain?: number;
    elevation_loss?: number;
    elevation_profile?: object[];
  }) =>
    request<SavedRoute>("/api/v1/routes", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  listRoutes: () => request<SavedRoute[]>("/api/v1/routes"),

  getRoute: (id: string) => request<SavedRouteDetail>(`/api/v1/routes/${id}`),

  deleteRoute: (id: string) =>
    request<{ ok: boolean }>(`/api/v1/routes/${id}`, { method: "DELETE" }),

  explore: (params: ExploreParams) =>
    request<ExploreResponse>("/api/v1/explore", {
      method: "POST",
      body: JSON.stringify(params),
    }),
};
