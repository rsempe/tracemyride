import json
import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

logger = logging.getLogger(__name__)
from geoalchemy2.shape import from_shape
from shapely.geometry import LineString
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.route import Route
from app.schemas.explore import ExploreRequest
from app.schemas.route import (
    ElevationRequest,
    GenerateRequest,
    RouteDetailResponse,
    RouteResponse,
    RouteSaveRequest,
    SnapRequest,
)
from app.services import elevation_service, valhalla_client
from app.services.elevation_service import compute_elevation_stats
from app.services.overpass_client import OverpassError, explore_routes
from app.services.route_generator import generate_route

router = APIRouter(prefix="/api/v1")


@router.post("/explore")
async def explore(req: ExploreRequest):
    try:
        result = await explore_routes(
            lat=req.lat,
            lng=req.lng,
            radius_km=req.radius_km,
            route_types=req.route_types,
        )
        return result
    except OverpassError as e:
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        logger.exception("Explore routes failed")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate")
async def generate(req: GenerateRequest):
    try:
        result = await generate_route(
            lat=req.lat,
            lng=req.lng,
            distance_km=req.distance_km,
            loop=req.loop,
            elevation_target=req.elevation_target,
            prefer_trails=req.prefer_trails,
        )
        return result
    except valhalla_client.ValhallaError as e:
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        logger.exception("Generate route failed")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/elevation/profile")
async def elevation_profile(req: ElevationRequest):
    profile = await elevation_service.get_elevation_profile(req.coordinates)
    gain, loss = compute_elevation_stats(profile)
    return {"profile": profile, "elevation_gain": gain, "elevation_loss": loss}


@router.post("/snap")
async def snap(req: SnapRequest):
    try:
        result = await valhalla_client.snap_to_road(req.coordinates)
        profile = await elevation_service.get_elevation_profile(result["coordinates"])
        gain, loss = compute_elevation_stats(profile)
        return {
            "type": "Feature",
            "geometry": {"type": "LineString", "coordinates": result["coordinates"]},
            "properties": {
                "distance_km": round(result["distance_km"], 2),
                "elevation_gain": gain,
                "elevation_loss": loss,
            },
            "elevation_profile": profile,
        }
    except valhalla_client.ValhallaError as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.post("/routes", response_model=RouteResponse)
async def save_route(req: RouteSaveRequest, db: AsyncSession = Depends(get_db)):
    coords = req.geojson.get("geometry", req.geojson).get("coordinates", [])
    if not coords:
        raise HTTPException(status_code=400, detail="No coordinates in geojson")

    line = LineString(coords)
    route = Route(
        name=req.name,
        geometry=from_shape(line, srid=4326),
        geojson=json.dumps(req.geojson),
        distance_km=req.distance_km,
        elevation_gain=req.elevation_gain,
        elevation_loss=req.elevation_loss,
        elevation_profile=json.dumps(req.elevation_profile) if req.elevation_profile else None,
    )
    db.add(route)
    await db.commit()
    await db.refresh(route)
    return route


@router.get("/routes", response_model=list[RouteResponse])
async def list_routes(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Route).order_by(Route.created_at.desc()))
    return result.scalars().all()


@router.get("/routes/{route_id}")
async def get_route(route_id: UUID, db: AsyncSession = Depends(get_db)):
    route = await db.get(Route, route_id)
    if not route:
        raise HTTPException(status_code=404, detail="Route not found")
    return {
        "id": route.id,
        "name": route.name,
        "distance_km": route.distance_km,
        "elevation_gain": route.elevation_gain,
        "elevation_loss": route.elevation_loss,
        "created_at": route.created_at,
        "geojson": json.loads(route.geojson),
        "elevation_profile": json.loads(route.elevation_profile) if route.elevation_profile else None,
    }


@router.delete("/routes/{route_id}")
async def delete_route(route_id: UUID, db: AsyncSession = Depends(get_db)):
    route = await db.get(Route, route_id)
    if not route:
        raise HTTPException(status_code=404, detail="Route not found")
    await db.delete(route)
    await db.commit()
    return {"ok": True}
