import httpx
import polyline as polyline_codec

from app.config import settings


class ValhallaError(Exception):
    pass


TRAIL_COSTING_OPTIONS = {
    "pedestrian": {
        "use_roads": 0.1,           # strongly prefer trails over roads
        "max_hiking_difficulty": 3,  # allow T3 (demanding mountain hiking) trails
        "sidewalk_factor": 1.5,     # roads with sidewalks are still roads, don't shortcut use_roads
    }
}

# Search radius (meters) for snapping waypoints to the nearest trail/road edge.
# Geometric waypoints from the fan algorithm can land far from any path.
INTERMEDIATE_SEARCH_RADIUS = 500


async def route(
    waypoints: list[tuple[float, float]],
    costing: str = "pedestrian",
    costing_options: dict | None = None,
) -> dict:
    """
    Get a route from Valhalla.
    waypoints: list of (lat, lng) tuples
    Returns dict with 'coordinates' (list of [lng, lat]) and 'distance_km'.
    """
    locations = []
    for i, (lat, lng) in enumerate(waypoints):
        loc: dict = {"lat": lat, "lon": lng}
        if 0 < i < len(waypoints) - 1:
            # Intermediate waypoints: use "through" so Valhalla can pass nearby
            # instead of routing to the exact nearest edge, and widen the search
            loc["type"] = "through"
            loc["radius"] = INTERMEDIATE_SEARCH_RADIUS
        else:
            loc["radius"] = INTERMEDIATE_SEARCH_RADIUS
        locations.append(loc)

    payload = {
        "locations": locations,
        "costing": costing,
        "costing_options": costing_options or TRAIL_COSTING_OPTIONS,
        "directions_options": {"units": "kilometers"},
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(f"{settings.valhalla_url}/route", json=payload)

    if resp.status_code != 200:
        raise ValhallaError(f"Valhalla error {resp.status_code}: {resp.text}")

    data = resp.json()
    trip = data["trip"]
    total_km = sum(leg["summary"]["length"] for leg in trip["legs"])

    # Decode polyline from all legs
    coords = []
    for leg in trip["legs"]:
        shape = leg["shape"]
        decoded = polyline_codec.decode(shape, 6)  # Valhalla uses precision 6
        leg_coords = [[lng, lat] for lat, lng in decoded]
        if coords:
            leg_coords = leg_coords[1:]  # avoid duplicate junction points
        coords.extend(leg_coords)

    return {"coordinates": coords, "distance_km": total_km}


async def snap_waypoint_to_trail(
    lat: float, lng: float, radius_m: float = 800,
) -> tuple[float, float] | None:
    """
    Use Valhalla's locate API to find the nearest path/track/footway edge
    near a waypoint. Returns (lat, lng) snapped to the best trail edge,
    or None if no trail found within radius.
    """
    payload = {
        "locations": [{"lat": lat, "lon": lng, "radius": int(radius_m)}],
        "costing": "pedestrian",
        "verbose": True,
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(f"{settings.valhalla_url}/locate", json=payload)

        if resp.status_code != 200:
            return None

        data = resp.json()
        for loc in data:
            edges = loc.get("edges", [])
            # Find the closest edge that is a trail/path/track
            for edge in edges:
                classification = edge.get("edge", {}).get("classification", {})
                use = classification.get("use", "")
                if use in PREFERRED_EDGE_USES:
                    # Return the snapped point on this edge
                    snap = edge.get("side_of_street", {})
                    snap_ll = edge.get("edge_info", {}).get("shape", [])
                    # Use the correlated lat/lon (closest point on the edge)
                    corr_lat = edge.get("correlated_lat")
                    corr_lon = edge.get("correlated_lon")
                    if corr_lat is not None and corr_lon is not None:
                        return (corr_lat, corr_lon)
                    # Fallback: use midpoint of the edge shape
                    if snap_ll and len(snap_ll) >= 2:
                        mid = snap_ll[len(snap_ll) // 2]
                        return (mid["lat"], mid["lon"])
        return None
    except Exception:
        return None


async def snap_to_road(coordinates: list[list[float]], costing: str = "pedestrian") -> dict:
    """
    Snap a list of [lng, lat] waypoints to the road network via Valhalla routing.
    Returns the same format as route().
    """
    waypoints = [(c[1], c[0]) for c in coordinates]  # convert [lng, lat] -> (lat, lng)
    return await route(waypoints, costing)


async def check_status() -> bool:
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{settings.valhalla_url}/status")
        return resp.status_code == 200
    except Exception:
        return False
