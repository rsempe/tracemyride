FROM python:3.11-slim

RUN apt-get update && \
    apt-get install -y --no-install-recommends git libgdal-dev gcc g++ && \
    rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir \
    flask \
    flask-caching \
    geographiclib \
    "numpy<2" \
    polyline \
    pyproj \
    pyyaml \
    rasterio

RUN git clone https://github.com/ajnisbet/opentopodata.git /app

WORKDIR /app

# Patch: fix rasterio f.index() crash with multiple points
RUN sed -i 's/tmp = f.index(xs.tolist(), ys.tolist(), op=_noop)/from rasterio.transform import rowcol; rows, cols = rowcol(f.transform, xs, ys, op=_noop)/' \
    opentopodata/backend.py && \
    sed -i '/print(f"{xs=}")/d' opentopodata/backend.py && \
    sed -i '/print(f"{ys=}")/d' opentopodata/backend.py && \
    sed -i '/print(f"{tmp=}")/d' opentopodata/backend.py && \
    sed -i '/rows, cols = tuple(tmp)/d' opentopodata/backend.py

EXPOSE 5001

ENV FLASK_APP=opentopodata/api.py
ENV DISABLE_MEMCACHE=1

CMD ["flask", "run", "--host", "0.0.0.0", "--port", "5001"]
