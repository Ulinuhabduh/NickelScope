# NickelScope v2

### Interactive AI-GIS Research Tool untuk Eksplorasi Nikel Laterit

> **ANTAM Hackathon 2026 — Young Mining Innovators** · Tema: **Eksplorasi**
> Studi kasus: **Sabuk Pomalaa–Kolaka, Sulawesi Tenggara**

NickelScope adalah **interactive research tool** — user gambar rectangle di peta,
model memprediksi probabilitas nikel laterit, lalu **SHAP Explainable AI**
menjelaskan **mengapa** model memutuskan begitu, lengkap dengan konteks geologis.

---

## Alur Kerja

```
User draws rectangle on map
        │
        ▼
Grid points generated (IDW interpolation)
        │
        ▼
Random Forest prediction → probability 0–1
        │
        ▼
SHAP TreeExplainer → feature contributions
        │
        ▼
Geological context → interpretation
```

---

## Cara Pakai

```bash
pip install -r requirements.txt
streamlit run app.py
```

1. Klik ikon **persegi** di pojok kiri atas peta
2. Gambar rectangle di area yang ingin diresearch
3. Klik **Retrieved GeoJSON** untuk submit
4. Lihat hasil: probability heatmap, SHAP analysis, geological context

---

## Arsitektur Sistem

| Komponen | Teknologi | Fungsi |
|----------|-----------|--------|
| Frontend | Streamlit + Folium | Map interaction, visualization |
| ML Model | Random Forest (400 trees) | Probabilistic prediction |
| XAI | SHAP TreeExplainer | Feature contribution explanation |
| Feature Eng | IDW Interpolation | Grid point feature extraction |
| Geology | GeoMap ESDM 1:100k | Lithological context |

---

## Struktur Repositori

```
NickelScope/
├── app.py                        # Interactive research tool (Streamlit v2)
├── gee/                          # Google Earth Engine scripts
│   ├── 01_aoi_explore.js
│   ├── 02_footprint_detect.js
│   ├── 03_sampling_points.js
│   ├── 04_feature_engineering.js
│   ├── 05_prospectivity_map.js
│   ├── 06_hostrock_features.js
│   └── 07_hostrock_map.js
├── ml/
│   ├── 01_train_model.py         # RF/XGBoost + spatial CV
│   ├── 02_hostrock_refine.py     # Host-rock constrained (final model)
│   └── outputs/                  # Trained model & metrics
├── data/                         # CSV features + raster
├── kolaka/                       # Peta geologi resmi (vektor)
├── figures/                      # Publication figures
├── docs/                         # Technical documentation
└── requirements.txt              # Python dependencies
```

---

## Fitur Input (8 Fitur)

| Fitur | Keterangan | Sumber |
|-------|-----------|--------|
| Iron Oxide | Rasio B4/B2 | Sentinel-2 |
| Ferrous | Rasio B11/B8 | Sentinel-2 |
| Clay | Rasio B11/B12 | Sentinel-2 |
| NDVI | Indeks Vegetasi | Sentinel-2 |
| Elevation | Ketinggian (m) | SRTM 30m |
| Slope | Kemiringan Lereng (°) | SRTM 30m |
| Curvature | Lengkungan Permukaan | SRTM 30m |
| TWI | Topographic Wetness Index | MERIT Hydro |

---

## Metodologi

### Anti-Circularity
Label training divalidasi terhadap peta geologi resmi. Label di luar host-rock
ultramafik dibuang untuk mencegah model mendeteksi "lahan terbuka" bukan "nikel laterit".

### Spatial Cross-Validation
Menggunakan block CV (3km grid) untuk mencegah spatial autocorrelation inflating metrics.

### Host-Rock Constraint
Prediksi hanya valid dalam buffer 500m dari ultramafic complex.

### Metrik

| Metode | Spatial CV AUC |
|--------|:-:|
| Naif (terkontaminasi) | 0.988 |
| **Host-Rock (valid)** | **0.986** |

---

## Sumber Data (100% Publik)

| Data | Sumber |
|------|--------|
| Sentinel-2 | Copernicus / GEE |
| DEM SRTM 30m | USGS / GEE |
| TWI | MERIT Hydro |
| Geologi 1:100k | GeoMap ESDM |

---

## Keterbatasan & Future Work
- Model condong ke fitur spektral → laterit tersingkap; prediksi di bawah tutupan perlu penguatan
- Label berbasis proxy permukaan; validasi lapangan diperlukan
- LLM chatbot untuk penjelasan natural language (rencana v3)

---

## ANTAM Hackathon 2026
