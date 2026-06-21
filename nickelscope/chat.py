"""AI Chatbot — NickelScope Assistant (OpenRouter)."""
import os
from openai import OpenAI

OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")
_client = None
_current_model = "openai/gpt-oss-120b:free"

MODELS = {
    "gpt-oss-120b": "openai/gpt-oss-120b:free",
    "nemotron-3-super": "nvidia/nemotron-3-super-120b-a12b:free",
}


def _switch_model(model_key):
    global _client, _current_model
    if model_key in MODELS:
        _current_model = MODELS[model_key]
        _client = None


def _get_client():
    global _client
    if _client is None:
        _client = OpenAI(api_key=OPENROUTER_API_KEY, base_url="https://openrouter.ai/api/v1")
    return _client


def _get_model_name():
    return _current_model


SYSTEM_PROMPT = """You are NickelScope Assistant, an expert AI geologist specializing in nickel laterite prospectivity analysis in Indonesia.

Your expertise covers:
- Nickel laterite formation processes (weathering of ultramafic/ophiolite rocks)
- Spectral remote sensing for mineral exploration (Sentinel-2 band ratios)
- DEM-based terrain analysis (slope, curvature, TWI) for laterite distribution
- Indonesian geology, particularly ophiolite belts and ultramafic complexes
- Prospectivity modeling and uncertainty interpretation

Key knowledge:
- Iron oxide ratio (B4/B2) indicates lateritic weathering intensity
- Ferrous ratio (B11/B8) detects mafic/ultramafic mineralogy
- Clay ratio (B11/B12) identifies clay-rich weathered zones
- NDVI helps distinguish vegetation cover from exposed laterite
- High TWI values suggest zones of accumulation favorable for laterization
- Nickel laterite forms primarily on serpentinized peridotite and dunite
- Major nickel belts in Indonesia: Pomalaa-Kolaka (Southeast Sulawesi), Buli (North Maluku), Gag Island (Raja Ampat), Weda (Central Halmahera)

Response guidelines:
- Be concise but technically precise
- Use bullet points for lists
- Reference specific band ratios or terrain metrics when explaining
- When prospectivity probability is high (>0.5), emphasize the geological significance
- When uncertainty is high, explain what additional data would reduce it
- Always relate findings to nickel laterite exploration potential
- Use markdown formatting for clarity"""


def build_context(state) -> str:
    """Build context string from current session state."""
    parts = []
    import math

    if state.aoi_bounds:
        b = state.aoi_bounds
        area_km = (b[2] - b[0]) * 111 * abs(math.cos(math.radians(b[1]))) * (b[3] - b[1]) * 111
        parts.append(f"Current AOI: [{b[0]:.4f}, {b[1]:.4f}] to [{b[2]:.4f}, {b[3]:.4f}] ({area_km:.1f} km²)")

    if state.geo_loaded:
        parts.append(f"Loaded geology provinces: {', '.join(state.geo_loaded)}")

    if state.last_grid is not None:
        g = state.last_grid
        parts.append(f"Processed grid: {len(g)} sample points")
        parts.append(f"Prospectivity — mean: {g.probability.mean():.3f}, max: {g.probability.max():.3f}, "
                      f"high-risk (>=0.5): {(g.probability >= 0.5).sum()}/{len(g)}")
        if 'uncertainty' in g.columns:
            parts.append(f"Mean uncertainty: {g.uncertainty.mean():.3f}")
        if 'rock_type' in g.columns:
            rock_dist = g.rock_type.value_counts().to_dict()
            parts.append(f"Rock types: {rock_dist}")
        top5 = g.nlargest(5, 'probability')[['lon', 'lat', 'probability']].to_dict('records')
        parts.append(f"Top-5 highest probability points:")
        for pt in top5:
            parts.append(f"  ({pt['lat']:.4f}, {pt['lon']:.4f}) → {pt['probability']:.3f}")

    return "\n".join(parts) if parts else "No AOI or processing data loaded yet."


def get_initial_message() -> str:
    """Welcome message for the chatbot."""
    return (
        "Hello! I'm **NickelScope Assistant**, your AI guide for nickel laterite prospectivity analysis.\n\n"
        "Draw a rectangle on the map and click **Process Area** to get started, then ask me anything!"
    )


def stream_response(message: str, history: list, state):
    """Stream a response from the active model."""
    context = build_context(state)
    messages = [{"role": "system", "content": SYSTEM_PROMPT + "\n\n[Session Context]\n" + context}]

    for msg in history[-4:]:
        role = "user" if msg["role"] == "user" else "assistant"
        content = msg["content"][:500] + "..." if len(msg["content"]) > 500 else msg["content"]
        messages.append({"role": role, "content": content})

    messages.append({"role": "user", "content": message})

    try:
        stream = _get_client().chat.completions.create(
            model=_get_model_name(),
            messages=messages,
            temperature=0.7,
            max_tokens=16384,
            stream=True,
        )
        for chunk in stream:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
    except Exception as e:
        yield f"Error: {e}"


def get_full_response(message: str, history: list, state) -> str:
    """Get full response at once (for non-blocking UI)."""
    return "".join(stream_response(message, history, state))
