from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class GenerateRequest(BaseModel):
    lat: float = Field(..., ge=-90, le=90)
    lng: float = Field(..., ge=-180, le=180)
    distance_km: float = Field(..., gt=0, le=100)
    loop: bool = True
    elevation_target: float | None = Field(None, ge=0, description="Target elevation gain in meters")


class ElevationRequest(BaseModel):
    coordinates: list[list[float]] = Field(..., description="List of [lng, lat] pairs")


class SnapRequest(BaseModel):
    coordinates: list[list[float]] = Field(..., description="List of [lng, lat] waypoints to snap")


class RouteSaveRequest(BaseModel):
    name: str = "Untitled Route"
    geojson: dict
    distance_km: float
    elevation_gain: float | None = None
    elevation_loss: float | None = None
    elevation_profile: list[dict] | None = None


class RouteResponse(BaseModel):
    id: UUID
    name: str
    distance_km: float
    elevation_gain: float | None
    elevation_loss: float | None
    created_at: datetime

    model_config = {"from_attributes": True}


class RouteDetailResponse(RouteResponse):
    geojson: dict
    elevation_profile: list[dict] | None

    model_config = {"from_attributes": True}
