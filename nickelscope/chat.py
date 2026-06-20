"""AI Chatbot — NickelScope Assistant (OpenRouter)."""
import os
from openai import OpenAI

OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")
_client = None


def _get_client():
    global _client
    if _client is None:
        _client = OpenAI(api_key=OPENROUTER_API_KEY, base_url="https://openrouter.ai/api/v1")
    return _client


def _get_model_name():
    return "openai/gpt-oss-120b:free"


SYSTEM_PROMPT = """You are NickelScope Assistant for nickel laterite prospectivity in Indonesia.
Use context data for specific answers. Be concise, educational. Use markdown."""


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
        "I can help you:\n"
        "- Interpret prospectivity results\n"
        "- Explain spectral indices and terrain features\n"
        "- Understand rock types and their significance\n"
        "- Answer questions about nickel laterite geology\n\n"
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
