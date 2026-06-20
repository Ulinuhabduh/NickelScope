"""Indonesia geology — lazy per-province loading."""
import pandas as pd
import geopandas as gpd
from pathlib import Path
from shapely.geometry import Point

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "geology_indonesia"

ULTRAMAFIC_KW = ["ultramafic", "serpentinite", "peridotite", "dunite",
                  "harzburgite", "komatiite", "ofiolit", "ophiolite"]
MAFIC_KW = ["mafic", "basalt", "gabbro", "diorite", "basa"]
FELSIC_KW = ["granitoid", "granite", "felsic", "felsik", "rhyolite", "asam"]
SED_KW = ["sediment", "clastic", "sandstone", "mudstone", "alluvium",
           "limestone", "sedimen", "klastik", "aluvial", "aluvium",
           "batupasir", "batulumpur", "batugamping", "konglomerat",
           "napal", "serpih", "batulempung", "batulanau"]
META_KW = ["metamorphic", "metamorf", "malihan", "pemalihan",
           "gneiss", "gneis", "schist", "sekis", "phyllite", "filit",
           "slate", "quartzite", "kuarsit", "marble", "pualam",
           "hornfels", "amphibolite", "ampibolit"]

ROCK_COLORS = {
    "ULTRAMAFIC": "#8B0000", "MAFIC": "#FF4500", "FELSIC": "#FFD700",
    "SEDIMENTARY": "#D2B48C", "METAMORPHIC": "#9370DB",
    "IGNEOUS": "#FF69B4", "OTHER": "#B0B0B0", "UNKNOWN": "#D3D3D3",
}

PROVINCE_DIRS = sorted([d.name for d in DATA_DIR.iterdir() if d.is_dir()])

_GPKG_TO_KEY = {
    "1. Geology NAD": "Aceh",
    "2. Geology Sumatera Utara": "Sumatera_Utara",
    "3. Geology Riau": "Riau",
    "4. Geology Kepulauan Riau": "Kepulauan_Riau",
    "5. Geology Sumatera Barat": "Sumatera_Barat",
    "6. Geology Jambi": "Jambi",
    "7. Geology Bengkulu": "Bengkulu",
    "8. Geology Sumatera Selatan": "Sumatera_Selatan",
    "9. Geology Lampung": "Lampung",
    "10. Geology Bangka Belitung": "Bangka_Belitung",
    "11. Geology Banten": "Banten",
    "12. Geology Jawa Barat": "Jawa_Barat",
    "13. Geology jawa Tengah": "Jawa_Tengah",
    "14. Geology Yogyakarta": "DI_Yogyakarta",
    "15. Geology Jawa Timur": "Jawa_Timur",
    "16. Geology DKI Jakarta": "DKI_Jakarta",
    "17. Geology Bali": "Bali",
    "18. Geology NTB": "Nusa_Tenggara_Barat",
    "19. Geology NTT": "Nusa_Tenggara_Timur",
    "20. Geology Kalimantan Barat": "Kalimantan_Barat",
    "21. Geology Kalimantan Tengah": "Kalimantan_Tengah",
    "22. Geology Kalimantan Selatan": "Kalimantan_Selatan",
    "23. Geology Kalimantan Timur": "Kalimantan_Timur",
    "24. Geology Kalimantan Utara": "Kalimantan_Utara",
    "25. Geology Sulawesi Selatan": "Sulawesi_Selatan",
    "26. Geology Sulawesi Tenggara": "Sulawesi_Tenggara",
    "27. Geology Sulawesi Tengah": "Sulawesi_Tengah",
    "28. Geology Gorontalo": "Gorontalo",
    "29. Geology Sulawesi Utara": "Sulawesi_Utara",
    "30. Geology Maluku Utara": "Maluku_Utara",
    "31. Geology Maluku": "Maluku",
    "32. Geology Papua Barat": "Papua_Barat",
    "33. Geology Papua": "Papua",
    "34. Geology Sulawesi Barat": "Sulawesi_Barat",
}
def _get_province_dirs():
    """Get province keys from gpkg (fallback to directory listing)."""
    gpkg = DATA_DIR / "geology_indonesia.gpkg"
    if gpkg.exists():
        try:
            import geopandas as gpd
            gdf = gpd.read_file(gpkg, columns=["PROVINSI"])
            if "PROVINSI" in gdf.columns:
                keys = []
                for prov in gdf["PROVINSI"].unique():
                    k = _GPKG_TO_KEY.get(prov)
                    if k:
                        keys.append(k)
                return sorted(keys)
        except Exception:
            pass
    return PROVINCE_DIRS

PROVINCE_LABELS = {
    "Aceh": "Nanggroe Aceh Darussalam",
    "Sumatera_Utara": "Sumatera Utara",
    "Sumatera_Barat": "Sumatera Barat",
    "Sumatera_Selatan": "Sumatera Selatan",
    "Kepulauan_Riau": "Kepulauan Riau",
    "Bangka_Belitung": "Kep. Bangka Belitung",
    "DI_Yogyakarta": "DI Yogyakarta",
    "DKI_Jakarta": "DKI Jakarta",
    "Jawa_Barat": "Jawa Barat",
    "Jawa_Tengah": "Jawa Tengah",
    "Jawa_Timur": "Jawa Timur",
    "Nusa_Tenggara_Barat": "NTB",
    "Nusa_Tenggara_Timur": "NTT",
    "Kalimantan_Utara": "Kalimantan Utara",
    "Kalimantan_Barat": "Kalimantan Barat",
    "Kalimantan_Selatan": "Kalimantan Selatan",
    "Kalimantan_Timur": "Kalimantan Timur",
    "Kalimantan_Tengah": "Kalimantan Tengah",
    "Sulawesi_Utara": "Sulawesi Utara",
    "Sulawesi_Barat": "Sulawesi Barat",
    "Sulawesi_Tengah": "Sulawesi Tengah",
    "Sulawesi_Selatan": "Sulawesi Selatan",
    "Sulawesi_Tenggara": "Sulawesi Tenggara",
    "Maluku_Utara": "Maluku Utara",
    "Papua_Barat": "Papua Barat",
}

_GPKG_KEY_TO_LABEL = {v: PROVINCE_LABELS.get(v, v.replace("_", " ")) for v in _GPKG_TO_KEY.values()}

_province_cache = {}
_full_gdf = None


def classify_rock(class_lith):
    if class_lith is None or (isinstance(class_lith, float) and pd.isna(class_lith)):
        return "UNKNOWN"
    cl = str(class_lith).lower()
    for kw in ULTRAMAFIC_KW:
        if kw in cl: return "ULTRAMAFIC"
    for kw in MAFIC_KW:
        if kw in cl: return "MAFIC"
    for kw in FELSIC_KW:
        if kw in cl: return "FELSIC"
    for kw in META_KW:
        if kw in cl: return "METAMORPHIC"
    for kw in SED_KW:
        if kw in cl: return "SEDIMENTARY"
    if "extrusive" in cl or "ekstrusi" in cl: return "IGNEOUS"
    if "intrusive" in cl or "intrusi" in cl or "intrusif" in cl or "plutonik" in cl: return "IGNEOUS"
    if "tektonit" in cl or "tectonite" in cl: return "ULTRAMAFIC"
    return "OTHER"


def _find_shp(province_dir):
    d = DATA_DIR / province_dir
    shps = list(d.rglob("*.shp"))
    return shps[0] if shps else None


def _load_full_gdf():
    """Load the merged gpkg once and cache it."""
    global _full_gdf
    if _full_gdf is None:
        gpkg = DATA_DIR / "geology_indonesia.gpkg"
        if gpkg.exists():
            _full_gdf = gpd.read_file(gpkg)
            if _full_gdf.crs and _full_gdf.crs.to_epsg() != 4326:
                _full_gdf = _full_gdf.to_crs("EPSG:4326")
    return _full_gdf


_KEY_TO_GPKG = {v: k for k, v in _GPKG_TO_KEY.items()}


def load_province(province_name):
    """Load a single province from gpkg or shapefile fallback. Returns GeoDataFrame with rock_type column."""
    if province_name in _province_cache:
        return _province_cache[province_name]

    full = _load_full_gdf()
    if full is not None and "PROVINSI" in full.columns:
        gpkg_name = _KEY_TO_GPKG.get(province_name, province_name)
        match = full[full["PROVINSI"] == gpkg_name].copy()
        if match.empty:
            match = full[full["PROVINSI"].str.lower() == province_name.lower()].copy()
        if not match.empty:
            match = match[~match.geometry.is_empty].copy()
            match["rock_type"] = match["CLASS_LITH"].apply(classify_rock) if "CLASS_LITH" in match.columns else "UNKNOWN"
            match["rock_color"] = match["rock_type"].map(ROCK_COLORS)
            match["PROVINSI"] = province_name
            _province_cache[province_name] = match
            return match

    shp = _find_shp(province_name)
    if shp is None:
        return None
    gdf = gpd.read_file(shp)
    gdf = gdf[~gdf.geometry.is_empty].copy()
    if gdf.crs and gdf.crs.to_epsg() != 4326:
        gdf = gdf.to_crs("EPSG:4326")
    gdf["rock_type"] = gdf["CLASS_LITH"].apply(classify_rock) if "CLASS_LITH" in gdf.columns else "UNKNOWN"
    gdf["rock_color"] = gdf["rock_type"].map(ROCK_COLORS)
    gdf["PROVINSI"] = province_name
    _province_cache[province_name] = gdf
    return gdf


def province_to_geojson(province_name, simplify_tolerance=0.003):
    """Load province and convert to GeoJSON dict for Leaflet."""
    gdf = load_province(province_name)
    if gdf is None:
        return None
    gdf = gdf.copy()
    gdf["geometry"] = gdf.geometry.simplify(simplify_tolerance, preserve_topology=True)
    gdf = gdf[~gdf.geometry.is_empty].copy()
    gdf = gdf[gdf.geometry.is_valid].copy()

    features = []
    for _, row in gdf.iterrows():
        geom = row.geometry
        if geom is None or geom.is_empty:
            continue

        def clean_ring(coords):
            return [[round(float(c[0]), 4), round(float(c[1]), 4)] for c in coords
                    if c[0] is not None and c[1] is not None
                    and float('-180') <= float(c[0]) <= 360 and float('-90') <= float(c[1]) <= 90]

        clean_coords = None
        if geom.geom_type == "Polygon":
            rings = [clean_ring(geom.exterior.coords)]
            for interior in geom.interiors:
                rings.append(clean_ring(interior.coords))
            rings = [r for r in rings if len(r) >= 4]
            if rings:
                clean_coords = rings
        elif geom.geom_type == "MultiPolygon":
            clean_coords = []
            for poly in geom.geoms:
                poly_rings = [clean_ring(poly.exterior.coords)]
                for interior in poly.interiors:
                    poly_rings.append(clean_ring(interior.coords))
                poly_rings = [r for r in poly_rings if len(r) >= 4]
                if poly_rings:
                    clean_coords.append(poly_rings)
            if not clean_coords:
                clean_coords = None
        if clean_coords is None:
            continue

        ft = row.get("FORMATION", "") or ""
        cl = row.get("CLASS_LITH", "") or ""
        rt = row.get("rock_type", "UNKNOWN")
        rc = row.get("rock_color", "#999")
        nm = row.get("NAME", "") or ""

        features.append({
            "type": "Feature",
            "properties": {
                "FORMATION": str(ft),
                "CLASS_LITH": str(cl),
                "NAME": str(nm),
                "rock_type": str(rt),
                "rock_color": str(rc),
            },
            "geometry": {
                "type": geom.geom_type,
                "coordinates": clean_coords,
            }
        })

    return {"type": "FeatureCollection", "features": features}


def _load_full():
    global _full_gdf
    if _full_gdf is None:
        import time
        t0 = time.time()
        _full_gdf = gpd.read_file(DATA_DIR / "geology_indonesia.gpkg")
        _full_gdf = _full_gdf[~_full_gdf.geometry.is_empty].copy()
        print(f"Full geology loaded in {time.time()-t0:.1f}s ({len(_full_gdf)} features)")
    return _full_gdf


def query_point(lon, lat):
    gdf = _load_full()
    pt = Point(lon, lat)
    hits = gdf[gdf.intersects(pt)]
    if len(hits) == 0:
        hits = gdf[gdf.intersects(pt.buffer(0.05))]
    if len(hits) == 0:
        return {"formation": "Unknown", "class_lith": "Unknown", "rock_type": "UNKNOWN",
                "name": "", "color": ROCK_COLORS["UNKNOWN"]}
    row = hits.iloc[0]
    cl = row["CLASS_LITH"] if not pd.isna(row["CLASS_LITH"]) else "Unknown"
    ft = row["FORMATION"] if not pd.isna(row["FORMATION"]) else "Unknown"
    nm = row["NAME"] if not pd.isna(row["NAME"]) else ""
    rt = classify_rock(cl)
    return {"formation": ft, "class_lith": cl, "rock_type": rt,
            "name": nm, "color": ROCK_COLORS[rt]}


def query_grid(lons, lats):
    results = []
    for lon, lat in zip(lons, lats):
        results.append(query_point(lon, lat))
    return pd.DataFrame(results)


def get_geology_legend_html():
    items = [
        ("ULTRAMAFIC", "Ultramafic / Ophiolite", "Host-rock for Ni laterite"),
        ("MAFIC", "Mafic (Basalt, Gabbro)", "Possible Ni source"),
        ("FELSIC", "Felsic (Granite, Rhyolite)", "Low Ni potential"),
        ("SEDIMENTARY", "Sedimentary", "Low Ni potential"),
        ("METAMORPHIC", "Metamorphic", "Evaluate"),
        ("IGNEOUS", "Igneous (unspecified)", "Evaluate"),
        ("OTHER", "Other / Unclassified", "—"),
    ]
    rows = ""
    for code, label, desc in items:
        c = ROCK_COLORS[code]
        rows += f'<i style="background:{c};width:12px;height:12px;display:inline-block;border:1px solid #ccc;"></i> <span style="color:black;">{label} <small>({desc})</small></span><br>'
    return f"""<div style="background:white;padding:8px 12px;border:1px solid #ddd;border-radius:6px;
     font-size:11px;color:black;display:inline-block;margin-top:4px;">
<b style="font-size:12px;color:black;">Geology Legend</b><br><hr style="margin:3px 0">
{rows}
<small style="color:#888;">Source: Indonesia Geospasial (34 provinces)</small>
</div>"""
