import math

EARTH_RADIUS_KM = 6371.0


def haversine(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Distance in km between two points."""
    lat1, lng1, lat2, lng2 = map(math.radians, [lat1, lng1, lat2, lng2])
    dlat = lat2 - lat1
    dlng = lng2 - lng1
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlng / 2) ** 2
    return 2 * EARTH_RADIUS_KM * math.asin(math.sqrt(a))


def destination_point(lat: float, lng: float, bearing_deg: float, distance_km: float) -> tuple[float, float]:
    """Compute destination point given start, bearing (degrees), and distance (km)."""
    lat_r = math.radians(lat)
    lng_r = math.radians(lng)
    bearing = math.radians(bearing_deg)
    d = distance_km / EARTH_RADIUS_KM

    lat2 = math.asin(
        math.sin(lat_r) * math.cos(d) + math.cos(lat_r) * math.sin(d) * math.cos(bearing)
    )
    lng2 = lng_r + math.atan2(
        math.sin(bearing) * math.sin(d) * math.cos(lat_r),
        math.cos(d) - math.sin(lat_r) * math.sin(lat2),
    )
    return math.degrees(lat2), math.degrees(lng2)


def bearing(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Initial bearing in degrees from point 1 to point 2."""
    lat1, lng1, lat2, lng2 = map(math.radians, [lat1, lng1, lat2, lng2])
    dlng = lng2 - lng1
    x = math.sin(dlng) * math.cos(lat2)
    y = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(dlng)
    return (math.degrees(math.atan2(x, y)) + 360) % 360
