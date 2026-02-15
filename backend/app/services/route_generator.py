import logging
import math
import random

from app.services import elevation_service, valhalla_client
from app.services.elevation_service import compute_elevation_stats, _batch_elevation_query
from app.services.overpass_client import get_trail_attractors
from app.utils.geo import bearing as geo_bearing, destination_point, haversine

logger = logging.getLogger(__name__)

MAX_ITERATIONS = 6
TOLERANCE = 0.15  # 15% distance tolerance
ELEVATION_TOLERANCE = 0.30  # 30% elevation tolerance
NUM_WAYPOINTS = 6
NUM_SCOUT_BEARINGS = 12  # sample elevation every 30°


async def generate_route(
    lat: float,
    lng: float,
    distance_km: float,
    loop: bool = True,
    elevation_target: float | None = None,
    prefer_trails: bool = True,
) -> dict:
    """
    Generate a running route using the "Waypoint Fan" strategy.

    When prefer_trails is set, fetches OSM trail data and biases waypoints
    toward marked trails. When elevation_target is also set, combines both
    elevation and trail density scoring to choose the best bearing.
    """
    scout_radius = distance_km / (2 * math.pi) if loop else distance_km * 0.35

    # Fetch trail attractors if requested
    trail_attractors: list[tuple[float, float]] = []
    if prefer_trails:
        try:
            trail_attractors = await get_trail_attractors(
                lat, lng, radius_km=scout_radius * 1.5
            )
        except Exception:
            logger.warning("Failed to fetch trail attractors, continuing without")

    # Determine best bearing
    best_bearing: float | None = None
    if elevation_target and trail_attractors:
        best_bearing = await _find_best_bearing(lat, lng, scout_radius, trail_attractors)
    elif elevation_target:
        best_bearing = await _find_best_bearing(lat, lng, scout_radius, [])
    elif trail_attractors:
        best_bearing = _find_trail_bearing(lat, lng, trail_attractors)

    if loop:
        result = await _generate_loop(lat, lng, distance_km, best_bearing, elevation_target, trail_attractors)
    else:
        result = await _generate_out_and_back(lat, lng, distance_km, best_bearing, elevation_target, trail_attractors)

    coords = result["coordinates"]

    # Remove out-and-back spurs to get a clean loop
    if loop:
        coords = _remove_spurs(coords)

    # Recalculate distance from cleaned coordinates
    total_km = _coords_distance_km(coords)

    # Get elevation profile
    profile = await elevation_service.get_elevation_profile(coords)
    gain, loss = compute_elevation_stats(profile)

    return {
        "type": "Feature",
        "geometry": {
            "type": "LineString",
            "coordinates": coords,
        },
        "properties": {
            "distance_km": round(total_km, 2),
            "elevation_gain": gain,
            "elevation_loss": loss,
        },
        "elevation_profile": profile,
    }


async def _find_best_bearing(
    lat: float,
    lng: float,
    radius_km: float,
    trail_attractors: list[tuple[float, float]],
) -> float:
    """
    Sample elevation at multiple bearings and combine with trail density.
    Returns the bearing (degrees) toward the best combined score.
    """
    coords = []
    bearings = []
    for i in range(NUM_SCOUT_BEARINGS):
        bearing_deg = i * (360.0 / NUM_SCOUT_BEARINGS)
        bearings.append(bearing_deg)
        wp_lat, wp_lng = destination_point(lat, lng, bearing_deg, radius_km)
        coords.append([wp_lng, wp_lat])  # [lng, lat] for elevation service

    elevations = await _batch_elevation_query(coords)

    # Normalize elevations to 0..1
    valid_elevs = [e for e in elevations if e is not None]
    min_elev = min(valid_elevs) if valid_elevs else 0
    max_elev = max(valid_elevs) if valid_elevs else 0
    elev_range = max_elev - min_elev if max_elev > min_elev else 1.0

    best_bearing = random.uniform(0, 360)
    best_score = -float("inf")
    for bearing_deg, elev in zip(bearings, elevations):
        elev_score = ((elev - min_elev) / elev_range) if elev is not None else 0.0
        trail_score = _trail_density_in_cone(lat, lng, bearing_deg, radius_km * 1.5, trail_attractors)

        if trail_attractors:
            score = 0.6 * elev_score + 0.4 * trail_score
        else:
            score = elev_score

        if score > best_score:
            best_score = score
            best_bearing = bearing_deg

    return best_bearing


def _find_trail_bearing(
    lat: float, lng: float, trail_attractors: list[tuple[float, float]]
) -> float | None:
    """Find the bearing toward the densest cluster of trail attractors."""
    if not trail_attractors:
        return None

    sector_size = 360.0 / NUM_SCOUT_BEARINGS
    counts = [0] * NUM_SCOUT_BEARINGS

    for a_lat, a_lng in trail_attractors:
        b = geo_bearing(lat, lng, a_lat, a_lng)
        idx = int(b / sector_size) % NUM_SCOUT_BEARINGS
        counts[idx] += 1

    max_count = max(counts)
    if max_count == 0:
        return None

    best_idx = counts.index(max_count)
    return best_idx * sector_size + sector_size / 2


def _trail_density_in_cone(
    lat: float,
    lng: float,
    bearing_deg: float,
    radius_km: float,
    trail_attractors: list[tuple[float, float]],
    half_angle: float = 15.0,
) -> float:
    """Count attractors within a directional cone, normalized to 0..1."""
    if not trail_attractors:
        return 0.0

    count = 0
    for a_lat, a_lng in trail_attractors:
        dist = haversine(lat, lng, a_lat, a_lng)
        if dist > radius_km:
            continue
        b = geo_bearing(lat, lng, a_lat, a_lng)
        diff = abs(b - bearing_deg)
        if diff > 180:
            diff = 360 - diff
        if diff <= half_angle:
            count += 1

    return min(count / 10.0, 1.0)


def _snap_toward_trail(
    wp_lat: float,
    wp_lng: float,
    trail_attractors: list[tuple[float, float]],
    strength: float = 0.4,
    max_dist_km: float = 2.0,
) -> tuple[float, float]:
    """Interpolate a waypoint toward the nearest trail attractor."""
    if not trail_attractors:
        return wp_lat, wp_lng

    nearest_dist = float("inf")
    nearest = None
    for a_lat, a_lng in trail_attractors:
        d = haversine(wp_lat, wp_lng, a_lat, a_lng)
        if d < nearest_dist:
            nearest_dist = d
            nearest = (a_lat, a_lng)

    if nearest is None or nearest_dist > max_dist_km:
        return wp_lat, wp_lng

    new_lat = wp_lat + strength * (nearest[0] - wp_lat)
    new_lng = wp_lng + strength * (nearest[1] - wp_lng)
    return new_lat, new_lng


async def _generate_loop(
    lat: float,
    lng: float,
    distance_km: float,
    uphill_bearing: float | None = None,
    elevation_target: float | None = None,
    trail_attractors: list[tuple[float, float]] | None = None,
) -> dict:
    """
    Waypoint Fan algorithm for loop routes.

    When elevation_target is set, elongates the polygon toward the peak so that
    uphill-facing waypoints are pushed further up the mountain.
    The elongation is then iteratively adjusted to match the target elevation gain.
    """
    if uphill_bearing is not None:
        # Offset so the peak falls between wp1 and wp2 (top of the polygon)
        base_angle = uphill_bearing - (360.0 / NUM_WAYPOINTS / 2)
    else:
        base_angle = random.uniform(0, 360)

    radius_km = distance_km / (2 * NUM_WAYPOINTS * math.sin(math.pi / NUM_WAYPOINTS))

    # Initial elongation estimate based on elevation target
    elongation = 1.0
    if elevation_target and uphill_bearing is not None:
        elongation = 1.0 + min(elevation_target / 1000.0, 3.0)

    best_result = None
    best_score = float("inf")

    for _ in range(MAX_ITERATIONS):
        waypoints = _compute_loop_waypoints(
            lat, lng, radius_km, base_angle, elongation, uphill_bearing,
            trail_attractors=trail_attractors or [],
        )
        result = await valhalla_client.route(waypoints)
        actual_km = result["distance_km"]
        distance_error = abs(actual_km - distance_km) / distance_km

        # Check elevation and compute combined score
        elev_error = 0.0
        if elevation_target and uphill_bearing is not None:
            profile = await elevation_service.get_elevation_profile(result["coordinates"])
            gain, _ = compute_elevation_stats(profile)
            elev_error = abs(gain - elevation_target) / elevation_target if elevation_target > 0 else 0.0

            # Adjust elongation toward elevation target
            if gain > 0:
                elev_ratio = elevation_target / gain
                elongation = max(1.0, min(elongation * elev_ratio, 5.0))

        # Track best result by combined score (distance + elevation)
        score = distance_error + elev_error
        if score < best_score:
            best_score = score
            best_result = result

        if distance_error <= TOLERANCE and elev_error <= ELEVATION_TOLERANCE:
            break

        # Adjust radius for distance
        ratio = distance_km / actual_km
        radius_km *= ratio

    return best_result


async def _generate_out_and_back(
    lat: float,
    lng: float,
    distance_km: float,
    uphill_bearing: float | None = None,
    elevation_target: float | None = None,
    trail_attractors: list[tuple[float, float]] | None = None,
) -> dict:
    """
    Out-and-back: one waypoint in the uphill direction.

    When elevation_target is set, pushes the turnaround waypoint further uphill
    and iteratively adjusts to match both distance and elevation gain.
    """
    bearing_deg = uphill_bearing if uphill_bearing is not None else random.uniform(0, 360)
    half_km = distance_km / 2
    # Mountain trails are very winding; use a lower factor when targeting elevation
    straight_factor = 0.5 if elevation_target else 0.7
    target_straight = half_km * straight_factor

    best_result = None
    best_score = float("inf")

    for _ in range(MAX_ITERATIONS):
        wp_lat, wp_lng = destination_point(lat, lng, bearing_deg, target_straight)
        if trail_attractors:
            wp_lat, wp_lng = _snap_toward_trail(wp_lat, wp_lng, trail_attractors, strength=0.5)
        waypoints = [(lat, lng), (wp_lat, wp_lng), (lat, lng)]
        result = await valhalla_client.route(waypoints)
        actual_km = result["distance_km"]
        distance_error = abs(actual_km - distance_km) / distance_km

        # Check elevation
        elev_error = 0.0
        if elevation_target and uphill_bearing is not None:
            profile = await elevation_service.get_elevation_profile(result["coordinates"])
            gain, _ = compute_elevation_stats(profile)
            elev_error = abs(gain - elevation_target) / elevation_target if elevation_target > 0 else 0.0

        # Track best result by combined score
        score = distance_error + elev_error
        if score < best_score:
            best_score = score
            best_result = result

        if distance_error <= TOLERANCE and elev_error <= ELEVATION_TOLERANCE:
            break

        # Adjust distance: scale straight-line estimate proportionally
        ratio = distance_km / actual_km
        target_straight *= ratio

    return best_result



def _compute_loop_waypoints(
    lat: float,
    lng: float,
    radius_km: float,
    base_angle: float,
    elongation: float = 1.0,
    uphill_bearing: float | None = None,
    trail_attractors: list[tuple[float, float]] | None = None,
) -> list[tuple[float, float]]:
    """
    Place waypoints around start point.

    When elongation > 1, waypoints facing the uphill_bearing are pushed further out,
    creating an elongated shape that reaches higher up the mountain.
    When trail_attractors are provided, each waypoint is snapped toward the nearest trail.
    """
    waypoints = [(lat, lng)]
    angle_step = 360.0 / NUM_WAYPOINTS
    for i in range(NUM_WAYPOINTS):
        angle = base_angle + i * angle_step

        if elongation != 1.0 and uphill_bearing is not None:
            # cos of angle difference: 1.0 when pointing uphill, -1.0 when downhill
            angle_diff = math.radians(angle - uphill_bearing)
            uphill_factor = max(0.0, math.cos(angle_diff))  # 0..1
            wp_radius = radius_km * (1.0 + (elongation - 1.0) * uphill_factor)
        else:
            wp_radius = radius_km

        wp_lat, wp_lng = destination_point(lat, lng, angle, wp_radius)

        if trail_attractors:
            wp_lat, wp_lng = _snap_toward_trail(
                wp_lat, wp_lng, trail_attractors, strength=0.4, max_dist_km=radius_km
            )

        waypoints.append((wp_lat, wp_lng))
    waypoints.append((lat, lng))  # close the loop
    return waypoints


def _remove_spurs(coords: list[list[float]], threshold_m: float = 30) -> list[list[float]]:
    """
    Remove out-and-back spurs from route coordinates.

    Scans the coordinate list for places where the route returns close to a
    previously visited point (within threshold_m). When found, the spur
    segment is cut and the route shortcuts directly.

    coords: list of [lng, lat]
    """
    if len(coords) < 20:
        return coords

    threshold_km = threshold_m / 1000.0
    min_spur = 6  # minimum points to be considered a spur (not noise)
    result = list(coords)

    changed = True
    while changed:
        changed = False
        max_spur = len(result) // 3  # a spur can't be more than 1/3 of the route
        i = 0
        while i < len(result) - min_spur:
            # Look forward for a point close to result[i]
            found_j = None
            for j in range(i + min_spur, min(i + max_spur, len(result))):
                dist = haversine(result[i][1], result[i][0], result[j][1], result[j][0])
                if dist < threshold_km:
                    found_j = j
                    break

            if found_j is not None:
                # Cut the spur: jump from i directly to j
                result = result[: i + 1] + result[found_j:]
                changed = True
                break  # restart scan from the beginning
            else:
                i += 1

    return result


def _coords_distance_km(coords: list[list[float]]) -> float:
    """Compute total distance in km from a list of [lng, lat] coordinates."""
    total = 0.0
    for i in range(1, len(coords)):
        total += haversine(
            coords[i - 1][1], coords[i - 1][0],
            coords[i][1], coords[i][0],
        )
    return total
