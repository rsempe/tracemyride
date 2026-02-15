# TraceMyRide

Smart trail & cycling route generator. Automatically generates loop or out-and-back itineraries based on starting position, target distance, and desired elevation gain. Also supports manual route drawing with snap-to-road.

## Prerequisites

- Docker & Docker Compose
- A regional OSM PBF file (e.g. `paca-latest.osm.pbf`) in `valhalla/data/`
- SRTM `.hgt` tiles in `elevation/data/`

### Data

```bash
# Download an OSM extract (example: PACA region, France)
mkdir -p valhalla/data
wget -O valhalla/data/paca-latest.osm.pbf \
  https://download.geofabrik.de/europe/france/provence-alpes-cote-d-azur-latest.osm.pbf

# Download SRTM tiles (example: tile covering 44°N 5°E)
mkdir -p elevation/data
# Download the required .hgt tiles from https://dwtkns.com/srtm30m/
```

## Getting Started

```bash
cp .env.example .env
docker compose up --build
```

On first launch, Valhalla builds its routing tiles (~5-10 min depending on PBF size).

## Services

| Service | Port | Description |
|---------|------|-------------|
| Frontend | 3000 | Next.js + MapLibre |
| Backend | 8000 | FastAPI |
| Valhalla | 8002 | Pedestrian routing |
| OpenTopoData | 5000 | SRTM elevation |
| PostgreSQL | 5432 | PostGIS |

## Verification

```bash
# Valhalla
curl http://localhost:8002/status

# Elevation
curl "http://localhost:5000/v1/srtm30m?locations=44.06,5.05"

# Route generation
curl -X POST http://localhost:8000/api/v1/generate \
  -H "Content-Type: application/json" \
  -d '{"lat":44.06,"lng":5.05,"distance_km":10,"loop":true}'
```
