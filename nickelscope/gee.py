"""Google Earth Engine — feature extraction & land cover sampling."""
import json
import os
import logging
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

PROJECT = "robotic-goal-480609-j0"
FEATS = ["iron_oxide", "ferrous", "clay", "ndvi",
         "elevation", "slope", "curvature", "twi"]


def init_gee():
    try:
        import ee

        try:
            ee.Initialize(project=PROJECT)
            return ee
        except Exception:
            pass

        sa_key = os.environ.get("GEE_SERVICE_ACCOUNT_KEY")
        if sa_key:
            try:
                creds = json.loads(sa_key)
                service_account = creds["client_email"]
                credentials = ee.ServiceAccountCredentials(service_account, key_data=sa_key)
                ee.Initialize(credentials, project=PROJECT)
                return ee
            except Exception as e:
                logger.warning("Service account init failed: %s", e)

        logger.warning("GEE initialization failed — running without Earth Engine")
        return None

    except ImportError:
        logger.warning("earthengine-api not installed — running without Earth Engine")
        return None


def _make_grid(lon_min, lat_min, lon_max, lat_max, n=400):
    n_side = int(np.sqrt(n))
    lons = np.linspace(lon_min, lon_max, n_side)
    lats = np.linspace(lat_min, lat_max, n_side)
    gl, gt = np.meshgrid(lons, lats)
    return [[float(a), float(b)] for a, b in zip(gl.ravel(), gt.ravel())]


def _s2_composite(ee, aoi):
    from ee import ImageCollection, Filter
    s2 = (ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
          .filterBounds(aoi).filterDate("2023-06-01", "2023-11-30")
          .filter(Filter.lt("CLOUDY_PIXEL_PERCENTAGE", 20))
          .median().clip(aoi))
    scl = s2.select("SCL")
    mask = scl.neq(3).And(scl.neq(8)).And(scl.neq(9)).And(scl.neq(10))
    return s2.updateMask(mask)


def build_gee_features(ee, lon_min, lat_min, lon_max, lat_max, scale=30, n_points=400):
    aoi = ee.Geometry.Rectangle([lon_min, lat_min, lon_max, lat_max])
    s2m = _s2_composite(ee, aoi)

    iron = s2m.select("B4").divide(s2m.select("B2")).rename("iron_oxide")
    ferr = s2m.select("B11").divide(s2m.select("B8")).rename("ferrous")
    clay = s2m.select("B11").divide(s2m.select("B12")).rename("clay")
    ndvi = s2m.normalizedDifference(["B8", "B4"]).rename("ndvi")

    dem = ee.Image("USGS/SRTMGL1_003").clip(aoi)
    elev = dem.rename("elevation")
    slope = ee.Terrain.slope(elev).rename("slope")
    curv = dem.convolve(ee.Kernel.laplacian8()).rename("curvature")

    merit = ee.Image("MERIT/Hydro/v1_0_1")
    upa = merit.select("upa").clip(aoi)
    tanS = slope.multiply(np.pi / 180).tan().max(0.001)
    twi = upa.multiply(1e6).divide(tanS).log().rename("twi")

    stack = ee.Image.cat([iron, ferr, clay, ndvi, elev, slope, curv, twi])
    pts = _make_grid(lon_min, lat_min, lon_max, lat_max, n_points)
    fc = ee.FeatureCollection([ee.Feature(ee.Geometry.Point(p)) for p in pts])
    result = stack.reduceRegions(collection=fc, reducer=ee.Reducer.first(), scale=scale).getInfo()

    rows = []
    for f in result["features"]:
        p = f["properties"]
        rows.append({
            "lon": f["geometry"]["coordinates"][0],
            "lat": f["geometry"]["coordinates"][1],
            **{feat: p.get(feat, 0) for feat in FEATS},
        })
    return pd.DataFrame(rows)


def get_geology_from_local(lon_min, lat_min, lon_max, lat_max, n_points=400):
    """Query real Indonesia geology shapefile for each grid point."""
    from nickelscope.geology import query_grid
    pts = _make_grid(lon_min, lat_min, lon_max, lat_max, n_points)
    lons = [p[0] for p in pts]
    lats = [p[1] for p in pts]
    return query_grid(lons, lats)
