from pydantic import BaseModel, Field


class ExploreRequest(BaseModel):
    lat: float = Field(..., ge=-90, le=90)
    lng: float = Field(..., ge=-180, le=180)
    radius_km: float = Field(5, ge=1, le=20)
    route_types: list[str] = Field(default=["hiking", "foot"])


class ExploredRoute(BaseModel):
    osm_id: int
    name: str | None
    ref: str | None
    route_type: str
    network: str | None
    distance: float | None
    geojson: dict


class ExploreResponse(BaseModel):
    routes: list[ExploredRoute]
    query_center: dict
    query_radius_km: float
