"use client";

import { useEffect, useRef, useCallback } from "react";
import maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import { useStore } from "@/lib/store";

const CARTO_STYLE =
  "https://basemaps.cartocdn.com/gl/voyager-gl-style/style.json";

const DEFAULT_CENTER: [number, number] = [5.05, 44.06]; // Provence
const DEFAULT_ZOOM = 13;

export default function MapView() {
  const mapContainer = useRef<HTMLDivElement>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);
  const userMarkerRef = useRef<maplibregl.Marker | null>(null);
  const hoverMarkerRef = useRef<maplibregl.Marker | null>(null);

  const route = useStore((s) => s.route);
  const mode = useStore((s) => s.mode);
  const drawingWaypoints = useStore((s) => s.drawingWaypoints);
  const addWaypoint = useStore((s) => s.addWaypoint);
  const setUserLocation = useStore((s) => s.setUserLocation);
  const userLocation = useStore((s) => s.userLocation);
  const hoveredRoutePoint = useStore((s) => s.hoveredRoutePoint);

  // Initialize map
  useEffect(() => {
    if (!mapContainer.current || mapRef.current) return;

    const map = new maplibregl.Map({
      container: mapContainer.current,
      style: CARTO_STYLE,
      center: DEFAULT_CENTER,
      zoom: DEFAULT_ZOOM,
    });

    map.addControl(new maplibregl.NavigationControl(), "top-right");

    map.on("load", () => {
      // Route line source
      map.addSource("route", {
        type: "geojson",
        data: { type: "FeatureCollection", features: [] },
      });
      map.addLayer({
        id: "route-line",
        type: "line",
        source: "route",
        paint: {
          "line-color": "#3b82f6",
          "line-width": 4,
          "line-opacity": 0.85,
        },
      });

      // Drawing waypoints source
      map.addSource("waypoints", {
        type: "geojson",
        data: { type: "FeatureCollection", features: [] },
      });
      map.addLayer({
        id: "waypoints-circles",
        type: "circle",
        source: "waypoints",
        paint: {
          "circle-radius": 7,
          "circle-color": "#ef4444",
          "circle-stroke-width": 2,
          "circle-stroke-color": "#ffffff",
        },
      });
    });

    mapRef.current = map;

    return () => {
      map.remove();
      mapRef.current = null;
    };
  }, []);

  // Geolocate
  useEffect(() => {
    if (!navigator.geolocation) return;
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        const loc: [number, number] = [pos.coords.longitude, pos.coords.latitude];
        setUserLocation(loc);
        if (mapRef.current) {
          mapRef.current.flyTo({ center: loc, zoom: 14 });
        }
      },
      () => {},
      { enableHighAccuracy: true, timeout: 10000 }
    );
  }, [setUserLocation]);

  // User location marker (draggable)
  useEffect(() => {
    if (!mapRef.current || !userLocation) return;
    if (userMarkerRef.current) {
      userMarkerRef.current.setLngLat(userLocation);
    } else {
      const el = document.createElement("div");
      el.style.width = "20px";
      el.style.height = "20px";
      el.style.borderRadius = "50%";
      el.style.backgroundColor = "#3b82f6";
      el.style.border = "3px solid white";
      el.style.boxShadow = "0 0 0 0 rgba(59,130,246,0.5)";
      el.style.cursor = "grab";
      el.style.animation = "marker-pulse 2s ease-out 1";

      if (!document.getElementById("marker-pulse-style")) {
        const style = document.createElement("style");
        style.id = "marker-pulse-style";
        style.textContent = `
          @keyframes marker-pulse {
            0% { box-shadow: 0 0 0 0 rgba(59,130,246,0.5); }
            70% { box-shadow: 0 0 0 12px rgba(59,130,246,0); }
            100% { box-shadow: 0 0 4px rgba(0,0,0,0.3); }
          }
        `;
        document.head.appendChild(style);
      }

      const marker = new maplibregl.Marker({ element: el, draggable: true })
        .setLngLat(userLocation)
        .addTo(mapRef.current);

      marker.on("dragend", () => {
        const lngLat = marker.getLngLat();
        setUserLocation([lngLat.lng, lngLat.lat]);
      });

      userMarkerRef.current = marker;
    }
  }, [userLocation, setUserLocation]);

  // Update route layer
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !map.isStyleLoaded()) return;

    const source = map.getSource("route") as maplibregl.GeoJSONSource | undefined;
    if (!source) return;

    if (route) {
      source.setData({
        type: "FeatureCollection",
        features: [
          {
            type: "Feature",
            geometry: route.geometry,
            properties: route.properties,
          },
        ],
      });

      // Fit bounds
      const coords = route.geometry.coordinates;
      if (coords.length > 1) {
        const bounds = coords.reduce(
          (b, c) => b.extend(c as [number, number]),
          new maplibregl.LngLatBounds(
            coords[0] as [number, number],
            coords[0] as [number, number]
          )
        );
        map.fitBounds(bounds, { padding: 60 });
      }
    } else {
      source.setData({ type: "FeatureCollection", features: [] });
    }
  }, [route]);

  // Update drawing waypoints layer
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !map.isStyleLoaded()) return;

    const source = map.getSource("waypoints") as maplibregl.GeoJSONSource | undefined;
    if (!source) return;

    source.setData({
      type: "FeatureCollection",
      features: drawingWaypoints.map((coord, i) => ({
        type: "Feature" as const,
        geometry: { type: "Point" as const, coordinates: coord },
        properties: { index: i },
      })),
    });
  }, [drawingWaypoints]);

  // Click handler: drawing mode adds waypoints, idle/viewing repositions start marker
  const handleMapClick = useCallback(
    (e: maplibregl.MapMouseEvent) => {
      if (mode === "drawing") {
        addWaypoint([e.lngLat.lng, e.lngLat.lat]);
      } else if (mode === "idle" || mode === "viewing") {
        setUserLocation([e.lngLat.lng, e.lngLat.lat]);
      }
    },
    [mode, addWaypoint, setUserLocation]
  );

  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;
    map.on("click", handleMapClick);
    return () => {
      map.off("click", handleMapClick);
    };
  }, [handleMapClick]);

  // Change cursor in drawing mode
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;
    map.getCanvas().style.cursor = mode === "drawing" ? "crosshair" : "";
  }, [mode]);

  // Elevation profile hover marker
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;

    if (hoveredRoutePoint) {
      if (hoverMarkerRef.current) {
        hoverMarkerRef.current.setLngLat(hoveredRoutePoint);
      } else {
        const el = document.createElement("div");
        el.style.width = "12px";
        el.style.height = "12px";
        el.style.borderRadius = "50%";
        el.style.backgroundColor = "#ef4444";
        el.style.border = "2px solid white";
        el.style.boxShadow = "0 0 4px rgba(0,0,0,0.4)";
        el.style.pointerEvents = "none";
        hoverMarkerRef.current = new maplibregl.Marker({ element: el })
          .setLngLat(hoveredRoutePoint)
          .addTo(map);
      }
    } else if (hoverMarkerRef.current) {
      hoverMarkerRef.current.remove();
      hoverMarkerRef.current = null;
    }
  }, [hoveredRoutePoint]);

  return <div ref={mapContainer} className="w-full h-full" />;
}
