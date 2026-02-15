import uuid
from datetime import datetime

from geoalchemy2 import Geometry
from sqlalchemy import Column, DateTime, Float, String, Text
from sqlalchemy.dialects.postgresql import UUID

from app.database import Base


class Route(Base):
    __tablename__ = "routes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False, default="Untitled Route")
    geometry = Column(Geometry("LINESTRING", srid=4326), nullable=False)
    geojson = Column(Text, nullable=False)
    distance_km = Column(Float, nullable=False)
    elevation_gain = Column(Float, nullable=True)
    elevation_loss = Column(Float, nullable=True)
    elevation_profile = Column(Text, nullable=True)  # JSON array of {distance, elevation}
    created_at = Column(DateTime, default=datetime.utcnow)
