"""
NickelScope v3 — NiceGUI Edition
Run: python app.py
"""
import warnings; warnings.filterwarnings("ignore")
import os
try:
    import certifi
    os.environ["SSL_CERT_FILE"] = certifi.where()
    os.environ["REQUESTS_CA_BUNDLE"] = certifi.where()
except Exception:
    pass
import numpy as np, pandas as pd, asyncio, json, tempfile
from pathlib import Path
from scipy.interpolate import griddata
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
import io, base64
from nicegui import ui, app
from starlette.requests import Request
from starlette.responses import PlainTextResponse

@app.get('/healthcheck')
def healthcheck():
    return PlainTextResponse('OK')

PROV_GEOJSON_DIR = Path(__file__).resolve().parent / "data" / "province_geojson"
PROV_GEOJSON_DIR.mkdir(parents=True, exist_ok=True)
app.add_static_files("/prov", str(PROV_GEOJSON_DIR))

OVERLAY_DIR = Path(__file__).resolve().parent / "data" / "overlays"
OVERLAY_DIR.mkdir(parents=True, exist_ok=True)
app.add_static_files("/overlays", str(OVERLAY_DIR))

STATIC_DIR = Path(__file__).resolve().parent / "static"
app.add_static_files("/ns-static", str(STATIC_DIR))

from nickelscope.geology import (
    query_point, get_geology_legend_html, ROCK_COLORS,
    classify_rock, PROVINCE_LABELS, _get_province_dirs,
    province_to_geojson,
)
from nickelscope.gee import init_gee, build_gee_features, get_geology_from_local, _make_grid
from nickelscope.ml import load_model, predict_grid, FEATS
from nickelscope.chat import get_initial_message, stream_response, get_full_response, _switch_model
from nickelscope.report import generate_report

model_dict = load_model()


def _ensure_province_geojson(prov_name):
    out = PROV_GEOJSON_DIR / f"{prov_name}.geojson"
    if out.exists():
        return True
    gj = province_to_geojson(prov_name, simplify_tolerance=0.003)
    if gj:
        out.write_text(json.dumps(gj), encoding="utf-8")
        return True
    return False


class State:
    aoi_bounds = None
    last_grid = None
    sat_layer = None
    interp_layer = None
    geo_loaded = set()
    profile_chart = None
    chat_history = []

state = State()

C = {'primary': '#1565C0', 'primary_dark': '#0D47A1', 'bg': '#F5F7FA', 'card': '#FFFFFF'}


@ui.page('/')
def main():
    ui.add_head_html(f'''
    <style>
        body {{ background: {C['bg']}; font-family: 'Segoe UI', system-ui, sans-serif; margin: 0; }}
        .ns-card {{ background: {C['card']}; border-radius: 12px; box-shadow: 0 2px 12px rgba(0,0,0,0.08); }}
        .ns-step-num {{ width: 26px; height: 26px; border-radius: 50%; background: {C['primary']};
                         color: white; display: flex; align-items: center; justify-content: center;
                         font-weight: 700; font-size: 12px; flex-shrink: 0; }}
    </style>
    ''')

    # ═══ HEADER ═══
    with ui.header().classes('items-center px-6 py-3').style(f'background: linear-gradient(135deg, {C["primary_dark"]}, {C["primary"]});'):
        ui.html('<svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="M12 2a14.5 14.5 0 0 0 0 20 14.5 14.5 0 0 0 0-20"/><path d="M2 12h20"/></svg>')
        with ui.column().classes('ml-2'):
            ui.label('NickelScope').classes('text-white text-lg font-bold leading-tight')
            ui.label('AI-GIS Nickel Laterite Prospectivity Tool').classes('text-white/70 text-xs')
        ui.space()
        ui.badge('v3.0').classes('bg-white/20 text-white')
        ui.badge('ANTAM Hackathon 2026').classes('bg-amber-500 text-white')

    # ═══ MAIN ═══
    with ui.column().classes('w-full max-w-[1600px] mx-auto p-4 gap-4'):

        # ── STEP GUIDE + SETTINGS ──
        with ui.card().classes('ns-card w-full p-4'):
            with ui.row().classes('w-full items-center justify-between flex-wrap gap-3'):
                with ui.row().classes('gap-4 items-center'):
                    for num, txt in [('1', 'Draw Rectangle'), ('2', 'Click Process'), ('3', 'View Results')]:
                        with ui.row().classes('gap-2 items-center'):
                            ui.html(f'<div class="ns-step-num">{num}</div>')
                            ui.label(txt).classes('text-xs text-gray-600')
                        ui.html('<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="#B0BEC5" stroke-width="2"><path d="M9 18l6-6-6-6"/></svg>')
                with ui.row().classes('gap-3 items-center'):
                    ui.label('Resolution').classes('text-xs text-gray-500')
                    resolution = ui.slider(min=10, max=30, value=20, step=1).classes('w-28')
                    ui.label('Scale').classes('text-xs text-gray-500 ml-2')
                    scale = ui.select(options=['30', '50', '100'], value='30').classes('w-20')

        # ── PROVINCE SELECTOR ──
        with ui.card().classes('ns-card w-full p-4'):
            ui.label('Geology Overlay — Select Province').classes('text-sm font-bold text-gray-600 mb-2')
            with ui.row().classes('w-full gap-3 items-center flex-wrap'):
                prov_labels = {d: PROVINCE_LABELS.get(d, d.replace("_", " ")) for d in _get_province_dirs()}
                prov_select = ui.select(
                    options=prov_labels,
                    value=[],
                    multiple=True,
                    clearable=True,
                ).classes('flex-1 min-w-[300px]')

        # ═══ MAP (FULL WIDTH) ═══
        with ui.card().classes('ns-card w-full p-2'):
            draw_control = {
                'draw': {'rectangle': True, 'polygon': False, 'marker': False,
                         'circle': False, 'polyline': True, 'circlemarker': False},
                'edit': {'edit': True, 'remove': True},
            }

            m = ui.leaflet(center=(-2.5, 118), zoom=5, draw_control=draw_control,
                           additional_resources=['/ns-static/ns-map-capture.js']) \
                .classes('w-full').style('height: 65vh; min-height: 400px; border-radius: 8px;')

            ee = init_gee()

            with ui.row().classes('w-full items-center gap-3 mt-2 px-2'):
                area_info = ui.label('No area selected').classes('text-sm text-gray-400 italic')
                ui.space()
                status_label = ui.label('').classes('text-xs text-gray-500')
                process_btn = ui.button('Process Area', icon='play_arrow').classes(
                    'bg-blue-600 text-white font-bold px-6 py-2 rounded-lg')

            ui.html(get_geology_legend_html())

        # ═══ RESULTS SECTION ═══
        results_section = ui.column().classes('w-full gap-4')

    # ────────────────────── PROVINCE GEOLOGY OVERLAY ──────────────────────
    state.geo_layers = {}

    async def load_province_geo(e):
        selected = prov_select.value or []

        to_remove = [p for p in state.geo_layers if p not in selected]
        for prov in to_remove:
            lid = state.geo_layers.pop(prov)
            try:
                m.run_method('remove_layer', lid)
            except Exception:
                pass

        await m.initialized()

        for prov in selected:
            if prov in state.geo_layers:
                continue
            status_label.set_text(f'Loading {PROVINCE_LABELS.get(prov, prov)}...')
            status_label.classes(replace='text-xs text-blue-500')
            await asyncio.to_thread(_ensure_province_geojson, prov)
            lid = f"geo_{prov}"
            geojson_url = f"/prov/{prov}.geojson"
            ui.run_javascript(f'''
            (function() {{
                var map = window.__ns_map;
                if (!map) {{ console.error("Map not found"); return; }}
                fetch("{geojson_url}")
                    .then(function(r) {{ return r.json(); }})
                    .then(function(gj) {{
                        L.geoJSON(gj, {{
                            style: function(f) {{
                                var rc = f.properties && f.properties.rock_color || '#999';
                                return {{ color: rc, weight: 0.5, opacity: 0.7, fillColor: rc, fillOpacity: 0.35 }};
                            }},
                            onEachFeature: function(f, layer) {{
                                var p = f.properties || {{}};
                                var rc = p.rock_color || '#999';
                                var info = '<div style="font-size:12px"><b>' + (p.FORMATION || 'N/A') + '</b><br>' +
                                    '<span style="color:#666">' + (p.CLASS_LITH || '') + '</span><br>' +
                                    '<b style="color:' + rc + '">' + (p.rock_type || '') + '</b></div>';
                                layer.bindPopup(info);
                                layer.bindTooltip(info, {{sticky: true, opacity: 0.95}});
                            }}
                        }}).addTo(map);
                        console.log("Geology loaded: {prov}");
                    }})
                    .catch(function(e) {{ console.error("Geology error:", e); }});
            }})();
            ''')
            state.geo_layers[prov] = lid

        status_label.set_text('')
        status_label.classes(replace='text-xs text-green-600')

    prov_select.on_value_change(load_province_geo)

    # ────────────────────── SATELLITE TOGGLE ──────────────────────
    def toggle_satellite(e):
        if e.value:
            if state.sat_layer is None and ee:
                try:
                    b = state.aoi_bounds or [95, -11, 141, 6]
                    aoi = ee.Geometry.Rectangle(b)
                    s2 = (ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
                          .filterBounds(aoi).filterDate("2023-06-01", "2023-11-30")
                          .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", 20))
                          .median().clip(aoi))
                    vis = s2.select(["B4", "B3", "B2"])
                    url = vis.getMapId({"min": 0, "max": 3000})["tile_fetcher"].url_format
                    state.sat_layer = m.tile_layer(url_template=url, options={'opacity': 0.8, 'name': 'Satellite'})
                except Exception as e:
                    ui.notify(f'Satellite error: {e}', type='warning')
        else:
            if state.sat_layer:
                try:
                    m.remove_layer(state.sat_layer)
                except Exception:
                    pass
                state.sat_layer = None

    show_sat = ui.switch(text='Satellite', value=False)
    show_sat.on_value_change(toggle_satellite)

    # ────────────────────── RESULTS RENDER ──────────────────────
    def show_results(grid, b):
        results_section.clear()
        mean_p = grid.probability.mean()
        max_p = grid.probability.max()
        n_high = (grid.probability >= 0.5).sum()
        n_total = len(grid)
        mean_u = grid.uncertainty.mean() if 'uncertainty' in grid.columns else 0

        with results_section:
            ui.separator()
            ui.label('Analysis Results').classes('text-lg font-bold text-gray-700 mt-2')

            with ui.row().classes('w-full gap-3'):
                _metric('Mean Prob.', f'{mean_p:.3f}', '#1565C0', '#E3F2FD')
                _metric('Max Prob.', f'{max_p:.3f}', '#C62828', '#FFEBEE')
                _metric('High-Risk (>=0.5)', str(n_high), '#F57F17', '#FFF8E1')
                _metric('Total Points', str(n_total), '#546E7A', '#ECEFF1')
                area_km = (b[2] - b[0]) * 111 * np.cos(np.radians(b[1])) * (b[3] - b[1]) * 111
                _metric('Area', f'{area_km:.1f} km\u00B2', '#2E7D32', '#E8F5E9')
                _metric('Mean Uncertainty', f'{mean_u:.3f}', '#7B1FA2', '#F3E5F5')

            with ui.row().classes('w-full gap-4 flex-nowrap'):
                with ui.card().classes('ns-card flex-1 min-w-0 p-4'):
                    ui.label('Probability Distribution').classes('text-sm font-bold text-gray-600 mb-2')
                    _chart_prob_dist(grid)
                with ui.card().classes('ns-card flex-1 min-w-0 p-4'):
                    ui.label('Rock Type Composition').classes('text-sm font-bold text-gray-600 mb-2')
                    _chart_rocktype(grid)
                with ui.card().classes('ns-card flex-1 min-w-0 p-4'):
                    ui.label('Uncertainty Distribution').classes('text-sm font-bold text-gray-600 mb-2')
                    _chart_uncertainty(grid)

            with ui.card().classes('ns-card w-full p-4'):
                ui.label('Cross-Section Profile').classes('text-sm font-bold text-gray-600 mb-2')
                ui.label('Draw a line on the map to see probability profile along transect.').classes('text-xs text-gray-400 mb-2')
                state.profile_chart = ui.column().classes('w-full')
                _show_profile_placeholder(state.profile_chart)

            if 'rock_type' in grid.columns:
                with ui.card().classes('ns-card w-full p-4'):
                    ui.label('Rock Type Detail').classes('text-sm font-bold text-gray-600 mb-2')
                    with ui.row().classes('w-full gap-2 flex-wrap'):
                        for rt, count in grid.rock_type.value_counts().items():
                            pct = 100 * count / n_total
                            color = ROCK_COLORS.get(rt, '#999')
                            _lc_card(rt, pct, color)

            with ui.card().classes('ns-card w-full p-4'):
                with ui.row().classes('w-full items-center mb-2'):
                    ui.label('Data Grid').classes('text-sm font-bold text-gray-600')
                    ui.space()
                    ui.button('Export CSV', icon='download', on_click=lambda: export_csv(grid)).classes(
                        'bg-green-600 text-white text-xs rounded-lg px-3')
                    ui.button('Export GeoJSON', icon='download', on_click=lambda: export_geojson(grid)).classes(
                        'bg-blue-600 text-white text-xs rounded-lg px-3')
                    ui.button('Export PDF', icon='picture_as_pdf', on_click=lambda: export_pdf(grid, b)).classes(
                        'bg-red-600 text-white text-xs rounded-lg px-3')
                    ui.button('New Analysis', icon='refresh', on_click=reset).classes(
                        'bg-gray-100 text-gray-600 text-xs rounded-lg')
                cols = ['lon', 'lat', 'probability', 'uncertainty', 'rock_type', 'formation'] + FEATS
                cols = [c for c in cols if c in grid.columns]
                ui.table.from_pandas(
                    grid[cols].sort_values('probability', ascending=False), pagination=10
                ).classes('w-full text-xs')

    def _metric(label, value, color, bg):
        with ui.card().classes('flex-1 p-3 text-center').style(f'background:{bg};border:none;'):
            ui.label(value).classes('text-xl font-bold').style(f'color:{color};')
            ui.label(label).classes('text-[9px] text-gray-500 uppercase tracking-wide')

    def _lc_card(name, pct, color):
        with ui.card().classes('p-3').style(f'border-left: 4px solid {color}; min-width: 180px;'):
            ui.label(name).classes('text-xs font-bold text-gray-700')
            ui.label(f'{pct:.1f}% area').classes('text-lg font-bold').style(f'color:{color};')

    # ────────────────────── CHARTS ──────────────────────
    def _chart_prob_dist(grid):
        bins = [0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
        counts = [int(((grid.probability >= bins[i]) & (grid.probability < bins[i + 1])).sum()) for i in range(len(bins) - 1)]
        labels = [f'{bins[i]:.1f}-{bins[i + 1]:.1f}' for i in range(len(bins) - 1)]
        colors = ['#1565C0', '#1976D2', '#1E88E5', '#2196F3', '#42A5F5', '#FFA726', '#FF9800', '#FB8C00', '#F57C00', '#EF6C00']
        ui.echart({
            'tooltip': {'trigger': 'axis'},
            'xAxis': {'type': 'category', 'data': labels, 'axisLabel': {'rotate': 45, 'fontSize': 9}},
            'yAxis': {'type': 'value', 'name': 'Count', 'nameTextStyle': {'fontSize': 10}},
            'series': [{'type': 'bar', 'data': [{'value': c, 'itemStyle': {'color': colors[i]}} for i, c in enumerate(counts)]}],
            'grid': {'left': 40, 'right': 10, 'top': 10, 'bottom': 40},
        }).classes('w-full').style('height: 220px;')

    def _chart_rocktype(grid):
        vc = grid.rock_type.value_counts()
        pie_data = [{'name': k, 'value': int(v)} for k, v in vc.items()]
        colors = [ROCK_COLORS.get(k, '#999') for k in vc.index]
        ui.echart({
            'tooltip': {'trigger': 'item', 'formatter': '{b}: {c} ({d}%)'},
            'series': [{'type': 'pie', 'radius': ['35%', '65%'], 'data': pie_data, 'label': {'fontSize': 9}, 'color': colors}],
            'grid': {'left': 0, 'right': 0, 'top': 0, 'bottom': 0},
        }).classes('w-full').style('height: 220px;')

    def _chart_uncertainty(grid):
        u = grid.uncertainty.values
        bins = np.linspace(0, max(u.max(), 0.01), 11)
        counts = [int(((u >= bins[i]) & (u < bins[i + 1])).sum()) for i in range(len(bins) - 1)]
        labels = [f'{bins[i]:.2f}' for i in range(len(bins) - 1)]
        ui.echart({
            'tooltip': {'trigger': 'axis'},
            'xAxis': {'type': 'category', 'data': labels, 'axisLabel': {'rotate': 45, 'fontSize': 8}},
            'yAxis': {'type': 'value', 'name': 'Count', 'nameTextStyle': {'fontSize': 10}},
            'series': [{'type': 'bar', 'data': counts, 'itemStyle': {'color': '#7B1FA2'}}],
            'grid': {'left': 40, 'right': 10, 'top': 10, 'bottom': 40},
        }).classes('w-full').style('height: 220px;')

    # ────────────────────── CROSS-SECTION ──────────────────────
    def _show_profile_placeholder(container):
        container.clear()
        with container:
            ui.label('Draw a line on the map to see the profile here.').classes('text-xs text-gray-400 italic py-4 text-center')

    def handle_line_draw(e):
        if state.last_grid is None or state.profile_chart is None:
            return
        if e.args.get('layerType') != 'polyline':
            return
        layer = e.args.get('layer', {})
        latlngs = layer.get('_latlngs', [])
        if not latlngs or len(latlngs) < 2:
            return
        pts = latlngs
        n_sample = 100
        lons = np.linspace(pts[0]['lng'], pts[-1]['lng'], n_sample)
        lats = np.linspace(pts[0]['lat'], pts[-1]['lat'], n_sample)
        grid = state.last_grid
        points = grid[['lon', 'lat']].values
        probs = grid['probability'].values
        uncs = grid['uncertainty'].values if 'uncertainty' in grid.columns else np.zeros(len(probs))
        dist = np.sqrt((lons - lons[0]) ** 2 + (lats - lats[0]) ** 2) * 111
        profile_p = griddata(points, probs, (lons, lats), method='linear')
        profile_u = griddata(points, uncs, (lons, lats), method='linear')
        profile_p = np.nan_to_num(profile_p, nan=0)
        profile_u = np.nan_to_num(profile_u, nan=0)
        state.profile_chart.clear()
        with state.profile_chart:
            ui.echart({
                'tooltip': {'trigger': 'axis'},
                'legend': {'data': ['Probability', 'Uncertainty'], 'bottom': 0, 'textStyle': {'fontSize': 10}},
                'xAxis': {'type': 'value', 'name': 'Distance (km)', 'nameLocation': 'center', 'nameGap': 25, 'nameTextStyle': {'fontSize': 10}},
                'yAxis': [
                    {'type': 'value', 'name': 'Probability', 'min': 0, 'max': 1, 'nameTextStyle': {'fontSize': 10}},
                    {'type': 'value', 'name': 'Uncertainty', 'nameTextStyle': {'fontSize': 10}},
                ],
                'series': [
                    {'name': 'Probability', 'type': 'line', 'data': [[round(float(d), 2), round(float(p), 4)] for d, p in zip(dist, profile_p)],
                     'smooth': True, 'lineStyle': {'color': '#1565C0', 'width': 2}, 'areaStyle': {'opacity': 0.1}, 'itemStyle': {'color': '#1565C0'}},
                    {'name': 'Uncertainty', 'type': 'line', 'yAxisIndex': 1, 'data': [[round(float(d), 2), round(float(u), 4)] for d, u in zip(dist, profile_u)],
                     'smooth': True, 'lineStyle': {'color': '#F44336', 'width': 1, 'type': 'dashed'}, 'itemStyle': {'color': '#F44336'}},
                ],
                'grid': {'left': 50, 'right': 50, 'top': 10, 'bottom': 50},
            }).classes('w-full').style('height: 250px;')

    m.on('draw:created', handle_line_draw)

    # ────────────────────── INTERPOLATION OVERLAY ──────────────────────
    def _add_interpolation_overlay(leaflet_map, grid, b):
        if state.interp_layer:
            try:
                leaflet_map.remove_layer(state.interp_layer)
            except Exception:
                pass
            state.interp_layer = None
        n_grid = 100
        xi = np.linspace(b[0], b[2], n_grid)
        yi = np.linspace(b[1], b[3], n_grid)
        xi, yi = np.meshgrid(xi, yi)
        points = grid[['lon', 'lat']].values
        values = grid['probability'].values
        zi = griddata(points, values, (xi, yi), method='cubic')
        zi = np.clip(np.nan_to_num(zi, nan=0), 0, 1)
        colors_list = ['#0D47A1', '#1565C0', '#42A5F5', '#80D8FF', '#E0F7FA', '#FFFF00', '#FFD54F', '#FFC107', '#FF9800', '#F44336', '#B71C1C']
        cmap = LinearSegmentedColormap.from_list('ni_prob', colors_list, N=256)
        fig, ax = plt.subplots(figsize=(8, 6))
        ax.pcolormesh(xi, yi, zi, cmap=cmap, shading='gouraud', vmin=0, vmax=1)
        ax.set_xlim(b[0], b[2]); ax.set_ylim(b[1], b[3]); ax.axis('off')
        fig.subplots_adjust(left=0, right=1, top=1, bottom=0)
        import hashlib, time
        fname = f"interp_{hashlib.md5(str(time.time()).encode()).hexdigest()[:8]}.png"
        fpath = OVERLAY_DIR / fname
        fig.savefig(str(fpath), format='png', dpi=100, bbox_inches='tight', pad_inches=0, transparent=True)
        plt.close(fig)
        state.interp_layer = leaflet_map.image_overlay(
            url=f'/overlays/{fname}',
            bounds=[[b[1], b[0]], [b[3], b[2]]],
            options={'opacity': 0.7}
        )

    # ────────────────────── EXPORT ──────────────────────
    def export_csv(grid):
        cols = ['lon', 'lat', 'probability', 'uncertainty', 'rock_type', 'formation', 'class_lith'] + FEATS
        cols = [c for c in cols if c in grid.columns]
        csv_bytes = grid[cols].to_csv(index=False).encode('utf-8')
        ui.download(csv_bytes, 'nickelscope_results.csv', media_type='text/csv')

    def export_geojson(grid):
        features = []
        for _, row in grid.iterrows():
            props = {k: float(row[k]) if isinstance(row[k], (np.floating, float)) else (int(row[k]) if isinstance(row[k], (np.integer, int)) else str(row[k]))
                     for k in grid.columns if k not in ['lon', 'lat']}
            features.append({
                'type': 'Feature',
                'geometry': {'type': 'Point', 'coordinates': [float(row['lon']), float(row['lat'])]},
                'properties': props,
            })
        geojson = {'type': 'FeatureCollection', 'features': features}
        geojson_bytes = json.dumps(geojson, indent=2).encode('utf-8')
        ui.download(geojson_bytes, 'nickelscope_results.geojson', media_type='application/json')

    def export_pdf(grid, b):
        try:
            pdf_bytes = generate_report(grid, b, geo_loaded=state.geo_loaded)
            ui.download(pdf_bytes, 'nickelscope_report.pdf', media_type='application/pdf')
        except Exception as e:
            ui.notify(f'PDF error: {e}', type='negative')

    # ────────────────────── PROCESS ──────────────────────
    async def on_process():
        if state.aoi_bounds is None:
            status_label.set_text('Draw a rectangle first!')
            status_label.classes(replace='text-xs text-red-500')
            return
        process_btn.disable()
        process_btn.props('loading')
        b = state.aoi_bounds
        s = int(scale.value)
        n = int(resolution.value) ** 2
        try:
            if ee is None:
                status_label.set_text('GEE not available. Using local data only...')
                status_label.classes(replace='text-xs text-yellow-600')
                grid = pd.DataFrame(_make_grid(b[0], b[1], b[2], b[3], n), columns=['lon', 'lat'])
                for feat in FEATS:
                    grid[feat] = 0.0
            else:
                status_label.set_text(f'Step 1/2 - Extracting features ({n} points)...')
                status_label.classes(replace='text-xs text-blue-500')
                grid = await asyncio.to_thread(build_gee_features, ee, b[0], b[1], b[2], b[3], scale=s, n_points=n)
            status_label.set_text('Step 2/2 - Querying geology data...')
            rock_data = await asyncio.to_thread(get_geology_from_local, b[0], b[1], b[2], b[3], n_points=n)
            grid['rock_type'] = rock_data['rock_type'].values[:len(grid)]
            grid['formation'] = rock_data['formation'].values[:len(grid)]
            grid['class_lith'] = rock_data['class_lith'].values[:len(grid)]
            grid['rock_color'] = rock_data['color'].values[:len(grid)]
            grid = predict_grid(grid, model_dict)
            state.last_grid = grid
            _add_interpolation_overlay(m, grid, b)
            status_label.set_text('Analysis complete!')
            status_label.classes(replace='text-xs text-green-600 font-bold')
            show_results(grid, b)
        except Exception as e:
            status_label.set_text(f'Error: {e}')
            status_label.classes(replace='text-xs text-red-600')
        finally:
            process_btn.enable()
            process_btn.props(remove='loading')

    def reset():
        state.aoi_bounds = None
        state.last_grid = None
        if state.interp_layer:
            try:
                m.remove_layer(state.interp_layer)
            except Exception:
                pass
            state.interp_layer = None
        if state.sat_layer:
            try:
                m.remove_layer(state.sat_layer)
            except Exception:
                pass
            state.sat_layer = None
        results_section.clear()
        area_info.set_text('No area selected')
        area_info.classes(replace='text-sm text-gray-400 italic')

    process_btn.on_click(on_process)

    # ────────────────────── DRAW EVENT ──────────────────────
    def handle_draw(e):
        if e.args.get('layerType') == 'rectangle':
            layer = e.args.get('layer', {})
            latlngs = layer.get('_latlngs', [])
            if latlngs and len(latlngs) > 0:
                coords = latlngs[0]
                lats = [c['lat'] for c in coords]
                lons = [c['lng'] for c in coords]
                state.aoi_bounds = [min(lons), min(lats), max(lons), max(lats)]
                b = state.aoi_bounds
                ax = (b[2] - b[0]) * 111 * np.cos(np.radians(b[1]))
                ay = (b[3] - b[1]) * 111
                area_info.set_text(f'Area: {ax:.1f} x {ay:.1f} km ({b[0]:.4f}, {b[1]:.4f}) -> ({b[2]:.4f}, {b[3]:.4f})')
                area_info.classes(replace='text-sm text-blue-600 font-semibold')
                status_label.set_text(f'Ready to process - {ax:.1f} x {ay:.1f} km')
                status_label.classes(replace='text-xs text-green-600')

    m.on('draw:created', handle_draw)

    # ══════════════════════════════ AI CHATBOT ══════════════════════════════
    ui.add_head_html('''
    <style>
        .ns-chat-drawer { background: #FAFBFC !important; }
        .ns-chat-header { background: linear-gradient(135deg, #0D47A1, #1565C0); padding: 14px 16px; }
        .ns-chat-msg { padding: 10px 14px !important; border-radius: 16px !important; font-size: 13px !important; line-height: 1.5 !important; display: block !important; width: fit-content !important; max-width: 96% !important; word-wrap: break-word !important; overflow-wrap: break-word !important; }
        .ns-chat-msg-user { background: #1565C0 !important; color: white !important; border-bottom-right-radius: 4px !important; margin-left: auto !important; }
        .ns-chat-msg-bot { background: white !important; border: 1px solid #E8EAF6 !important; border-bottom-left-radius: 4px !important; }
        .ns-chat-msg p { margin: 0 0 4px 0 !important; }
        .ns-chat-msg p:last-child { margin-bottom: 0 !important; }
        .ns-chat-msg ul, .ns-chat-msg ol { margin: 4px 0 !important; padding-left: 20px !important; }
        .ns-chat-msg code { font-size: 12px !important; background: #f5f5f5 !important; padding: 1px 4px !important; border-radius: 3px !important; }
        .ns-chat-msg pre { background: #1e1e1e !important; color: #d4d4d4 !important; padding: 8px !important; border-radius: 8px !important; overflow-x: auto !important; white-space: pre-wrap !important; font-size: 12px !important; }
        .ns-chat-msg pre code { background: transparent !important; padding: 0 !important; color: inherit !important; }
        .ns-chat-msg table { border-collapse: collapse !important; font-size: 11px !important; width: 100% !important; table-layout: fixed !important; }
        .ns-chat-msg th, .ns-chat-msg td { border: 1px solid #ddd !important; padding: 4px 8px !important; white-space: normal !important; word-wrap: break-word !important; overflow-wrap: break-word !important; }
        .ns-chat-input { background: white; border: 2px solid #E8EAF6; border-radius: 24px !important; transition: border-color 0.2s; }
        .ns-chat-input:focus-within { border-color: #1565C0 !important; box-shadow: 0 0 0 3px rgba(21,101,192,0.1); }
        .ns-chat-chip { background: white; border: 1px solid #E3F2FD; border-radius: 14px !important; font-size: 10px !important; color: #1565C0 !important; padding: 2px 8px !important; min-height: 20px !important; transition: all 0.2s; }
        .ns-chat-chip:hover { background: #E3F2FD !important; border-color: #1565C0 !important; transform: translateY(-1px); }
        .ns-typing-dot { animation: ns-bounce 1.4s infinite ease-in-out both; }
        .ns-typing-dot:nth-child(1) { animation-delay: -0.32s; }
        .ns-typing-dot:nth-child(2) { animation-delay: -0.16s; }
        @keyframes ns-bounce { 0%,80%,100% { transform: scale(0); } 40% { transform: scale(1); } }
    </style>
    <script>
    document.addEventListener('DOMContentLoaded', function() {
        setTimeout(function() {
            var win = document.querySelector('.ns-chat-window');
            var header = win ? win.querySelector('[class*="ns-chat-header"]') : null;
            if (!win || !header) return;
            var offsetX = 0, offsetY = 0, isDragging = false;
            header.addEventListener('mousedown', function(e) {
                isDragging = true;
                offsetX = e.clientX - win.getBoundingClientRect().left;
                offsetY = e.clientY - win.getBoundingClientRect().top;
                win.style.transition = 'none';
            });
            document.addEventListener('mousemove', function(e) {
                if (!isDragging) return;
                win.style.left = (e.clientX - offsetX) + 'px';
                win.style.top = (e.clientY - offsetY) + 'px';
                win.style.right = 'auto';
                win.style.bottom = 'auto';
            });
            document.addEventListener('mouseup', function() { isDragging = false; });
        }, 500);
    });
    </script>
    </style>
    ''')

    # ── Floating Chat Window ──
    chat_window = ui.element('div').classes('ns-chat-window').style('''
        position: fixed; bottom: 80px; right: 24px; width: 400px; height: 520px;
        min-width: 320px; min-height: 300px; max-width: 90vw; max-height: 90vh;
        background: white; border-radius: 16px; box-shadow: 0 8px 32px rgba(0,0,0,0.25);
        display: none; flex-direction: column; z-index: 9999; overflow: hidden;
        border: 1px solid #E0E0E0; resize: both;
    ''')

    with chat_window:
        # ── Header (draggable) ──
        with ui.row().classes('ns-chat-header w-full items-center gap-3').style('cursor: move;'):
            with ui.avatar().classes('bg-white/20'):
                ui.html('<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="M12 2a14.5 14.5 0 0 0 0 20 14.5 14.5 0 0 0 0-20"/><path d="M2 12h20"/></svg>')
            with ui.column().classes('ml-1'):
                ui.label('NickelScope Assistant').classes('text-white text-sm font-bold')
                ui.label('Powered by OpenRouter').classes('text-white/60 text-xs')
            ui.space()
            model_select = ui.select(
                options={'gpt-oss-120b': 'GPT OSS 120B', 'nemotron-3-super': 'Nemotron 3 Super'},
                value='gpt-oss-120b',
                on_change=lambda e: _switch_model(e.value),
            ).classes('w-44').props('dense outlined standout dark color=white')
            ui.button(icon='minimize', on_click=lambda: ui.run_javascript('document.querySelector(".ns-chat-window").style.display="none"')).props('flat round dense color=white size=sm')
            ui.button(icon='close', on_click=lambda: (ui.run_javascript('document.querySelector(".ns-chat-window").style.display="none"'), ui.run_javascript('document.querySelectorAll("[class*=\'fixed bottom-6 right-6\']")[0].style.display=\'flex\''))).props('flat round dense color=white size=sm')

        # ── Chat Messages (scrollable) ──
        chat_container = ui.column().classes('flex-1 overflow-y-auto w-full gap-3 p-3 min-w-0')

        with chat_container:
            with ui.card().classes('ns-chat-msg ns-chat-msg-bot'):
                ui.markdown(get_initial_message())

        # ── Suggestion Chips ──
        with ui.row().classes('w-full gap-1 px-3 py-1 flex-wrap justify-center items-center').style('border-top: 1px solid #F0F0F0; background: #FAFBFC;'):
            ui.label('Quick:').classes('text-xs text-gray-400 mr-1')
            for chip in ['Iron oxide?', 'Prospective rocks?', 'TWI?']:
                def _make_chip_handler(text):
                    return lambda: _send_chat(text)
                ui.button(chip, on_click=_make_chip_handler(chip)).classes('ns-chat-chip')

        # ── Input Area ──
        with ui.row().classes('w-full items-center gap-2 px-3 py-2').style('background: white; border-top: 1px solid #E8EAF6;'):
            with ui.card().classes('ns-chat-input flex-1 items-center').style('padding: 2px 8px;'):
                chat_input = ui.input(placeholder='Ask about nickel laterite geology...').classes('w-full').props('borderless dense')
            send_btn = ui.button(icon='send').props('round color=primary size=sm')

    async def _send_chat(question=None):
        if question is None:
            question = chat_input.value.strip()
        if not question:
            return
        chat_input.value = ''

        state.chat_history.append({"role": "user", "content": question})
        with chat_container:
            with ui.card().classes('ns-chat-msg ns-chat-msg-user ml-auto'):
                ui.label(question).classes('text-sm')

        send_btn.props('remove=icon=send')
        send_btn.props('add=icon=loop')
        send_btn.props('loading')
        chat_input.disable()

        with chat_container:
            typing_card = ui.card().classes('ns-chat-msg ns-chat-msg-bot')
            with typing_card:
                spinner_row = ui.row().classes('items-center gap-1')
                with spinner_row:
                    for i in range(3):
                        ui.html(f'<div class="ns-typing-dot" style="width:7px;height:7px;border-radius:50%;background:#90A4AE;display:inline-block;margin:0 2px;"></div>')

        ui.run_javascript('document.querySelector(".ns-chat-window").scrollTop = 99999')

        import queue, threading
        q = queue.Queue()
        def _run():
            try:
                for chunk in stream_response(question, state.chat_history, state):
                    q.put(chunk)
            except Exception:
                pass
            finally:
                q.put(None)
        threading.Thread(target=_run, daemon=True).start()

        response_text = ''
        update_counter = 0
        while True:
            try:
                chunk = q.get_nowait()
            except queue.Empty:
                await asyncio.sleep(0.05)
                continue
            if chunk is None:
                break
            response_text += chunk
            update_counter += 1
            if update_counter % 3 == 0 or len(chunk) > 10:
                with typing_card.clear():
                    ui.markdown(response_text)
                ui.run_javascript('document.querySelector(".ns-chat-window").scrollTop = 99999')

        with typing_card.clear():
            ui.markdown(response_text)
        ui.run_javascript('document.querySelector(".ns-chat-window").scrollTop = 99999')

        state.chat_history.append({"role": "assistant", "content": response_text})

        send_btn.props('remove=icon=loop')
        send_btn.props('add=icon=send')
        send_btn.props(remove='loading')
        chat_input.enable()

    send_btn.on_click(_send_chat)
    chat_input.on('keydown.enter', _send_chat)

    # FAB to toggle chat
    chat_fab = ui.button(icon='chat').classes('fixed bottom-6 right-6 z-[9999] shadow-lg').props('round color=primary fab')

    def toggle_chat():
        ui.run_javascript('''
            var win = document.querySelector(".ns-chat-window");
            var fab = document.querySelector("[class*='fixed bottom-6 right-6']");
            if (win.style.display === "none" || win.style.display === "") {
                win.style.display = "flex";
                fab.style.display = "none";
            } else {
                win.style.display = "none";
                fab.style.display = "flex";
            }
        ''')

    chat_fab.on_click(toggle_chat)

ui.run(title='NickelScope', host='0.0.0.0', port=int(os.environ.get('PORT', 8080)), reload=False, show=False)
