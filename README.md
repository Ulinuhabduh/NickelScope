# NickelScope v3

### Interactive AI-GIS Research Tool for Nickel Laterite Prospectivity

> **ANTAM Hackathon 2026 — Young Mining Innovators** · Theme: **Exploration**
> Case study: **Pomalaa–Kolaka Belt, Southeast Sulawesi**

NickelScope is an **interactive AI-GIS research tool** — users draw a rectangle on a map,
GEE extracts features in real-time, ML predicts prospectivity probability,
geological context is displayed, and an AI chatbot assists with interpretation.

---

## Workflow

```
User draws rectangle on map
        │
        ▼
Real-time GEE feature extraction (Sentinel-2, SRTM, MERIT Hydro)
        │
        ▼
Random Forest prediction → probability 0–1 + uncertainty
        │
        ▼
Geological context → rock type classification
        │
        ▼
AI Chatbot (Groq GPT OSS 120B) → natural language interpretation
        │
        ▼
PDF Report → professional multi-page export
```

---

## How to Use

```bash
pip install -r requirements.txt
python app.py
```

1. Click the **rectangle** icon on the map (top-left)
2. Draw a rectangle over the area of interest
3. Click **Process Area** to extract features and predict
4. View results: probability heatmap, cross-section, rock types
5. Ask the AI chatbot for interpretation
6. Export results as CSV, GeoJSON, or PDF report

---

## Architecture

| Component | Technology | Function |
|-----------|-----------|----------|
| Frontend | NiceGUI + Leaflet | Map interaction, real-time UI |
| ML Model | Random Forest (400 trees) | Probabilistic prediction + uncertainty |
| Feature Eng | Google Earth Engine | Real-time Sentinel-2, SRTM, MERIT Hydro |
| Geology | GeoMap ESDM 1:100k | 34 province lithological overlay |
| AI Chat | Groq GPT OSS 120B | Natural language interpretation |
| Report | ReportLab | Multi-page PDF generation |
| Deployment | Docker + Railway | Cloud deployment |

---

## Project Structure

```
NickelScope/
├── app.py                    # Main NiceGUI application
├── nickelscope/
│   ├── __init__.py
│   ├── geology.py            # Rock classification, province loading
│   ├── gee.py                # Google Earth Engine feature extraction
│   ├── ml.py                 # Model loading + prediction
│   ├── chat.py               # AI chatbot (Groq)
│   ├── report.py             # PDF report generator
│   └── maps.py               # Legacy Folium maps (unused)
├── static/
│   └── ns-map-capture.js     # Leaflet draw event capture
├── ml/outputs/
│   └── nickelscope_model_hostrock.joblib
├── data/
│   ├── geology_indonesia/    # Merged GeoPackage (80MB)
│   └── province_geojson/     # Cached province GeoJSON
├── Dockerfile
├── railway.json
├── render.yaml
└── requirements.txt
```

---

## Input Features (8 Features)

| Feature | Description | Source |
|---------|-------------|--------|
| Iron Oxide | B4/B2 ratio | Sentinel-2 |
| Ferrous | B11/B8 ratio | Sentinel-2 |
| Clay | B11/B12 ratio | Sentinel-2 |
| NDVI | Vegetation index | Sentinel-2 |
| Elevation | Height (m) | SRTM 30m |
| Slope | Slope angle (deg) | SRTM 30m |
| Curvature | Surface curvature | SRTM 30m |
| TWI | Topographic Wetness Index | MERIT Hydro |

---

## Methodology

### Anti-Circularity
Training labels validated against official geological maps. Labels outside
ultramafic host-rock zones are removed to prevent the model from detecting
"open land" instead of "nickel laterite".

### Spatial Cross-Validation
Block CV (3km grid) used to prevent spatial autocorrelation from inflating metrics.

### Host-Rock Constraint
Predictions are only valid within 500m buffer of ultramafic complexes.

### Metrics

| Method | Spatial CV AUC |
|--------|:-:|
| Naive (contaminated) | 0.988 |
| **Host-Rock (valid)** | **0.986** |

---

## Data Sources (100% Public)

| Data | Source |
|------|--------|
| Sentinel-2 | Copernicus / GEE |
| DEM SRTM 30m | USGS / GEE |
| TWI | MERIT Hydro |
| Geology 1:100k | GeoMap ESDM (34 provinces) |

---

## Deployment

### Railway (Recommended)
```bash
# Push to GitHub
git init && git add . && git commit -m "Deploy"
git remote add origin https://github.com/username/nickelscope.git
git push -u origin main

# Deploy on Railway
# 1. Connect GitHub repo
# 2. Railway auto-detects Dockerfile
# 3. Set environment variables:
#    - GROQ_API_KEY: your Groq API key
#    - GEE_SERVICE_ACCOUNT_KEY: GCP service account JSON
# 4. Deploy
```

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `GROQ_API_KEY` | Groq API key for AI chatbot | Yes |
| `GEE_SERVICE_ACCOUNT_KEY` | GCP service account JSON for Earth Engine | Optional (fallback to local auth) |
| `PORT` | Server port (auto-set by Railway) | No |

---

## Limitations & Future Work
- Model biased toward spectral features → laterite at surface; subsurface predictions need reinforcement
- Labels based on surface proxy; field validation required
- Geological overlay could be improved with more detailed formations

---

## ANTAM Hackathon 2026
