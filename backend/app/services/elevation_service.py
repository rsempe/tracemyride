import httpx

from app.config import settings

BATCH_SIZE = 100  # OpenTopoData max per request


async def get_elevation_profile(
    coordinates: list[list[float]],
) -> list[dict]:
    """
    Get elevation for a list of [lng, lat] coordinates.
    Returns list of {distance_km, elevation, lat, lng}.
    """
    # Sample coordinates if too many (keep ~200 points for a smooth profile)
    sampled = _sample_coords(coordinates, max_points=200)

    elevations = await _batch_elevation_query(sampled)

    # Build profile with cumulative distance
    profile = []
    cumulative_km = 0.0
    for i, (coord, elev) in enumerate(zip(sampled, elevations)):
        if i > 0:
            cumulative_km += _haversine_simple(
                sampled[i - 1][1], sampled[i - 1][0], coord[1], coord[0]
            )
        profile.append({
            "distance_km": round(cumulative_km, 3),
            "elevation": elev,
            "lat": coord[1],
            "lng": coord[0],
        })

    return profile


async def _batch_elevation_query(coordinates: list[list[float]]) -> list[float | None]:
    """Query OpenTopoData in batches."""
    all_elevations = []
    for i in range(0, len(coordinates), BATCH_SIZE):
        batch = coordinates[i : i + BATCH_SIZE]
        locations = "|".join(f"{c[1]},{c[0]}" for c in batch)

        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                f"{settings.elevation_url}/v1/srtm30m",
                params={"locations": locations},
            )

        if resp.status_code == 200:
            data = resp.json()
            for result in data.get("results", []):
                all_elevations.append(result.get("elevation"))
        else:
            all_elevations.extend([None] * len(batch))

    return all_elevations


def compute_elevation_stats(profile: list[dict]) -> tuple[float, float]:
    """Compute total elevation gain and loss from a profile."""
    gain = 0.0
    loss = 0.0
    for i in range(1, len(profile)):
        prev = profile[i - 1].get("elevation")
        curr = profile[i].get("elevation")
        if prev is not None and curr is not None:
            diff = curr - prev
            if diff > 0:
                gain += diff
            else:
                loss += abs(diff)
    return round(gain, 1), round(loss, 1)


def _sample_coords(coords: list[list[float]], max_points: int) -> list[list[float]]:
    if len(coords) <= max_points:
        return coords
    step = len(coords) / max_points
    sampled = [coords[int(i * step)] for i in range(max_points - 1)]
    sampled.append(coords[-1])
    return sampled


def _haversine_simple(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    import math

    R = 6371.0
    lat1, lng1, lat2, lng2 = map(math.radians, [lat1, lng1, lat2, lng2])
    dlat = lat2 - lat1
    dlng = lng2 - lng1
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlng / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))
