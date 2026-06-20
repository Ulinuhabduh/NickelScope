"""Folium map builders & layers (legacy Streamlit version)."""
import branca.colormap as cm
from .geology import ROCK_COLORS


def build_map(center=(-2.5, 118), zoom=5):
    import folium
    from folium.plugins import Draw
    m = folium.Map(location=list(center), zoom_start=zoom, tiles="CartoDB positron")
    Draw(
        position="topleft",
        draw_options={"rectangle": True, "polyline": False, "polygon": False,
                      "circle": False, "circlemarker": False},
        edit_options={"edit": True, "remove": True},
    ).add_to(m)
    return m


def add_geology_overlay(m, ee):
    pass


def add_geology_legend(m):
    pass


def add_prediction_heatmap(m, grid_df):
    import folium
    cm.LinearColormap(
        colors=["#000080", "#0000ff", "#00ffff", "#ffff00", "#ff8000", "#ff0000"],
        vmin=0, vmax=1, caption="Nickel Prospectivity Probability"
    ).add_to(m)
    for _, row in grid_df.iterrows():
        p = row.probability
        c = "#ff0000" if p >= 0.7 else "#ff8000" if p >= 0.5 else "#ffff00" if p >= 0.3 else "#00ffff" if p >= 0.1 else "#000080"
        folium.CircleMarker(
            location=[row.lat, row.lon], radius=4, color=c,
            fill=True, fill_opacity=0.7, weight=0,
            popup=f"Prob: {p:.3f}",
        ).add_to(m)
