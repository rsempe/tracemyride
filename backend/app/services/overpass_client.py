import logging
import math

import httpx

logger = logging.getLogger(__name__)

OVERPASS_URL = "https://overpass-api.de/api/interpreter"

ALLOWED_ROUTE_TYPES = {"hiking", "foot", "running", "bicycle", "mtb"}


class OverpassError(Exception):
    pass


def _build_query(lat: float, lng: float, radius_m: int, route_types: list[str]) -> str:
    safe_types = [rt for rt in route_types if rt in ALLOWED_ROUTE_TYPES]
    if not safe_types:
        safe_types = ["hiking", "foot"]

    type_filter = "|".join(safe_types)
    return f"""
[out:json][timeout:30];
(
  relation["type"="route"]["route"~"^({type_filter})$"](around:{radius_m},{lat},{lng});
);
out body;
>;
out skel qt;
"""


def _haversine(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    R = 6371.0
    rlat1, rlng1, rlat2, rlng2 = map(math.radians, [lat1, lng1, lat2, lng2])
    dlat = rlat2 - rlat1
    dlng = rlng2 - rlng1
    a = math.sin(dlat / 2) ** 2 + math.cos(rlat1) * math.cos(rlat2) * math.sin(dlng / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _assemble_geometry(members: list[dict], nodes_map: dict) -> dict | None:
    """Assemble way members into a LineString or MultiLineString GeoJSON geometry."""
    lines: list[list[list[float]]] = []

    for member in members:
        if member.get("type") != "way":
            continue
        nds = member.get("geometry", [])
        if not nds:
            continue
        coords = [[pt["lon"], pt["lat"]] for pt in nds if "lon" in pt and "lat" in pt]
        if len(coords) < 2:
            continue
        lines.append(coords)

    if not lines:
        return None

    # Try to merge consecutive lines
    merged: list[list[list[float]]] = [lines[0]]
    for line in lines[1:]:
        tail = merged[-1][-1]
        head = line[0]
        rev_head = line[-1]

        if tail[0] == head[0] and tail[1] == head[1]:
            merged[-1].extend(line[1:])
        elif tail[0] == rev_head[0] and tail[1] == rev_head[1]:
            merged[-1].extend(list(reversed(line))[1:])
        else:
            merged.append(line)

    if len(merged) == 1:
        return {"type": "LineString", "coordinates": merged[0]}
    return {"type": "MultiLineString", "coordinates": merged}


def _compute_distance(geometry: dict) -> float | None:
    """Compute approximate total distance in km from a GeoJSON geometry."""
    if geometry["type"] == "LineString":
        coords = geometry["coordinates"]
    elif geometry["type"] == "MultiLineString":
        coords = []
        for line in geometry["coordinates"]:
            coords.extend(line)
    else:
        return None

    total = 0.0
    for i in range(1, len(coords)):
        total += _haversine(coords[i - 1][1], coords[i - 1][0], coords[i][1], coords[i][0])
    return round(total, 2)


def _parse_element(element: dict, ways_by_id: dict, nodes_map: dict) -> dict | None:
    """Transform an Overpass relation element into an ExploredRoute-compatible dict."""
    tags = element.get("tags", {})
    members = element.get("members", [])

    # Build geometry from member ways
    way_members = []
    for m in members:
        if m.get("type") == "way" and m.get("ref") in ways_by_id:
            way_members.append(ways_by_id[m["ref"]])

    if not way_members:
        return None

    geometry = _assemble_geometry(way_members, nodes_map)
    if not geometry:
        return None

    distance = _compute_distance(geometry)

    geojson = {
        "type": "Feature",
        "geometry": geometry,
        "properties": {
            "osm_id": element["id"],
            "name": tags.get("name"),
            "ref": tags.get("ref"),
            "route_type": tags.get("route", "unknown"),
            "network": tags.get("network"),
        },
    }

    return {
        "osm_id": element["id"],
        "name": tags.get("name"),
        "ref": tags.get("ref"),
        "route_type": tags.get("route", "unknown"),
        "network": tags.get("network"),
        "distance": distance,
        "geojson": geojson,
    }


def _sample_points_from_geometry(geometry: dict, interval_km: float = 0.2) -> list[tuple[float, float]]:
    """Sample (lat, lng) points along a GeoJSON geometry at regular intervals."""
    if geometry["type"] == "LineString":
        lines = [geometry["coordinates"]]
    elif geometry["type"] == "MultiLineString":
        lines = geometry["coordinates"]
    else:
        return []

    points: list[tuple[float, float]] = []
    for coords in lines:
        if len(coords) < 2:
            continue
        accum = 0.0
        # Emit the first point
        points.append((coords[0][1], coords[0][0]))  # (lat, lng)
        for i in range(1, len(coords)):
            seg = _haversine(coords[i - 1][1], coords[i - 1][0], coords[i][1], coords[i][0])
            accum += seg
            if accum >= interval_km:
                points.append((coords[i][1], coords[i][0]))
                accum = 0.0
    return points


async def get_trail_attractors(
    lat: float,
    lng: float,
    radius_km: float,
    route_types: list[str] | None = None,
    sample_interval_km: float = 0.2,
) -> list[tuple[float, float]]:
    """Fetch OSM trail routes and sample attractor points along their geometries."""
    try:
        result = await explore_routes(lat, lng, radius_km=radius_km, route_types=route_types)
    except OverpassError:
        logger.warning("Overpass query failed for trail attractors, falling back to no trails")
        return []

    attractors: list[tuple[float, float]] = []
    for route in result.get("routes", []):
        geom = route.get("geojson", {}).get("geometry")
        if geom:
            attractors.extend(_sample_points_from_geometry(geom, sample_interval_km))
    return attractors


async def explore_routes(
    lat: float,
    lng: float,
    radius_km: float = 5,
    route_types: list[str] | None = None,
) -> dict:
    if route_types is None:
        route_types = ["hiking", "foot"]

    radius_m = int(radius_km * 1000)
    query = _build_query(lat, lng, radius_m, route_types)

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(OVERPASS_URL, data={"data": query})
    except httpx.TimeoutException:
        raise OverpassError("Overpass API timeout — try a smaller radius")

    if resp.status_code == 429:
        raise OverpassError("Overpass API rate limit — please wait a moment and retry")

    if resp.status_code != 200:
        raise OverpassError(f"Overpass API error {resp.status_code}: {resp.text[:200]}")

    data = resp.json()
    elements = data.get("elements", [])

    # Index nodes and ways
    nodes_map: dict[int, dict] = {}
    ways_by_id: dict[int, dict] = {}
    relations: list[dict] = []

    for el in elements:
        if el["type"] == "node":
            nodes_map[el["id"]] = el
        elif el["type"] == "way":
            # Resolve node refs to geometry
            geometry = []
            for nd_id in el.get("nodes", []):
                if nd_id in nodes_map:
                    n = nodes_map[nd_id]
                    geometry.append({"lat": n["lat"], "lon": n["lon"]})
            el["geometry"] = geometry
            ways_by_id[el["id"]] = el
        elif el["type"] == "relation":
            relations.append(el)

    routes = []
    for rel in relations:
        parsed = _parse_element(rel, ways_by_id, nodes_map)
        if parsed:
            routes.append(parsed)

    return {
        "routes": routes,
        "query_center": {"lat": lat, "lng": lng},
        "query_radius_km": radius_km,
    }
