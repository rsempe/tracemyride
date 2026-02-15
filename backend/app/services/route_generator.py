import math
import random

from app.services import elevation_service, valhalla_client
from app.services.elevation_service import compute_elevation_stats, _batch_elevation_query
from app.utils.geo import destination_point, haversine

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
) -> dict:
    """
    Generate a running route using the "Waypoint Fan" strategy.

    When elevation_target is set, scouts terrain in all directions, orients
    waypoints toward the highest ground, and iteratively adjusts to match
    both the target distance and elevation gain.
    """
    # Scout for uphill direction when elevation target is set
    uphill_bearing = None
    if elevation_target:
        scout_radius = distance_km / (2 * math.pi) if loop else distance_km * 0.35
        uphill_bearing = await _find_uphill_bearing(lat, lng, scout_radius)

    if loop:
        result = await _generate_loop(lat, lng, distance_km, uphill_bearing, elevation_target)
    else:
        result = await _generate_out_and_back(lat, lng, distance_km, uphill_bearing, elevation_target)

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


async def _find_uphill_bearing(lat: float, lng: float, radius_km: float) -> float:
    """
    Sample elevation at multiple bearings around the start point.
    Returns the bearing (degrees) toward the highest ground.
    """
    coords = []
    bearings = []
    for i in range(NUM_SCOUT_BEARINGS):
        bearing_deg = i * (360.0 / NUM_SCOUT_BEARINGS)
        bearings.append(bearing_deg)
        wp_lat, wp_lng = destination_point(lat, lng, bearing_deg, radius_km)
        coords.append([wp_lng, wp_lat])  # [lng, lat] for elevation service

    elevations = await _batch_elevation_query(coords)

    best_bearing = random.uniform(0, 360)  # fallback if all elevations fail
    best_elev = -float("inf")
    for bearing_deg, elev in zip(bearings, elevations):
        if elev is not None and elev > best_elev:
            best_elev = elev
            best_bearing = bearing_deg

    return best_bearing


async def _generate_loop(
    lat: float,
    lng: float,
    distance_km: float,
    uphill_bearing: float | None = None,
    elevation_target: float | None = None,
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
            lat, lng, radius_km, base_angle, elongation, uphill_bearing
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
) -> list[tuple[float, float]]:
    """
    Place waypoints around start point.

    When elongation > 1, waypoints facing the uphill_bearing are pushed further out,
    creating an elongated shape that reaches higher up the mountain.
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
