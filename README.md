# 🛰️⛏️ NickelScope

### AI–GIS Prospectivity Mapping untuk Eksplorasi Nikel Laterit Berbasis Penginderaan Jauh

> **ANTAM Hackathon 2026 — Young Mining Innovators** · Tema: **Eksplorasi**
> Studi kasus: **Sabuk Pomalaa–Kolaka, Sulawesi Tenggara**

NickelScope adalah sistem AI–GIS yang memetakan **probabilitas keterdapatan nikel
laterit** dari fusi citra satelit, DEM, dan peta geologi resmi — menghasilkan
**peta target bor prioritas** yang **dibatasi oleh host-rock (ultramafik)** dan
divalidasi secara geologis, untuk menekan biaya, waktu, dan dampak lingkungan eksplorasi.

---

## 🎯 Ringkasan & Pendekatan

Pipeline ini dibangun **100% dari data publik & open-source**:

1. **Pelabelan** — footprint laterit terbuka dideteksi dari citra Sentinel-2
   (indeks besi + NDVI) lalu di-sampling jadi titik berlabel.
2. **Feature engineering** — 8 fitur: spektral (iron-oxide, ferrous, clay, NDVI)
   + topografi (elevasi, slope, curvature, TWI).
3. **Pemodelan** — Random Forest / XGBoost dengan **spatial (block) cross-validation**
   agar estimasi performa jujur (bukan random split).
4. **Host-Rock Constraint** — divalidasi dengan **peta geologi resmi 1:100k (GeoMap ESDM)**:
   label di luar ultramafik disaring, prediksi dibatasi ke host-rock valid.

### 🔑 Temuan kunci (inti metodologi)

Model spektral naif memberi **Spatial AUC 0.988** yang **menyesatkan** —
sebagian besar "positif" ternyata terkontaminasi (lahan terbuka non-ultramafik).
Setelah dibersihkan dengan host-rock constraint:

| Model | Spatial CV AUC | Catatan |
|-------|:---:|---------|
| Naif (terkontaminasi) | 0.988 | Mendeteksi lahan terbuka — circular |
| **Host-Rock Constrained** | **0.986** | **Valid geologis** (133 false-positive dibuang) |

> Validasi geologi mengungkap **42%** titik positif awal benar-benar berada di
> ultramafik; sisanya tersebar di formasi sedimen (median 1,3 km dari host-rock).
> Penyaringan ini membuat model jujur tanpa kehilangan akurasi.

---

## 📁 Struktur Repositori

```
NickelScope/
├── gee/                      # Google Earth Engine scripts (alur akuisisi → peta)
│   ├── 01_aoi_explore.js         AOI + indeks besi (eksplorasi awal)
│   ├── 02_footprint_detect.js    deteksi & verifikasi footprint laterit
│   ├── 03_sampling_points.js     sampling titik label dari poligon
│   ├── 04_feature_engineering.js ekstraksi 8 fitur → features.csv
│   ├── 05_prospectivity_map.js   peta prospektivitas v1
│   ├── 06_hostrock_features.js   fitur geologi + re-extract
│   └── 07_hostrock_map.js        peta final host-rock constrained
├── ml/
│   ├── 01_train_model.py         RF/XGBoost + spatial CV
│   ├── 02_hostrock_refine.py     host-rock constrained refine (model jujur)
│   └── outputs/                  model & metrik terlatih
├── data/                     # CSV titik/fitur + raster prospektivitas final
├── kolaka/                   # peta geologi resmi (vektor) + ultramafik (host-rock)
├── figures/                  # 10 figure siap-proposal (peta profesional)
├── figures_src.py            # generator figure (script)
├── NickelScope_Figures.ipynb # generator figure (notebook)
├── docs/                     # panduan teknis
├── NickelScope-Konsep.md     # konsep & 7 komponen proposal
└── NickelScope-Workflow.tex  # rencana kerja lengkap (LaTeX → PDF)
```

---

## 🔄 Cara Reproduksi

**A. Akuisisi data (Google Earth Engine)** — butuh akun GEE gratis
1. Jalankan `gee/01`–`gee/04` di [code.earthengine.google.com](https://code.earthengine.google.com)
   → ekspor `nickelscope_labels.csv` & `nickelscope_features_v2.csv` ke `data/`.

**B. Pemodelan & validasi (Python)**
```bash
pip install -r requirements.txt
python ml/01_train_model.py        # model awal + spatial CV
python ml/02_hostrock_refine.py    # host-rock constrained (model jujur)
```

**C. Peta final & figure**
1. Upload `kolaka/ultramafic_kolaka.zip` sebagai asset GEE, jalankan `gee/07`
   → ekspor `nickelscope_prospectivity_hostrock.tif` ke `data/`.
2. Jalankan notebook `NickelScope_Figures.ipynb` (atau `python figures_src.py`)
   → 10 figure ke `figures/`.

---

## 🗂️ Sumber Data (publik & legal)

| Data | Sumber |
|------|--------|
| Citra multispektral Sentinel-2 | Copernicus / Google Earth Engine |
| DEM (SRTM 30 m) | USGS / Google Earth Engine |
| Flow accumulation (TWI) | MERIT Hydro |
| Peta Geologi 1:100k (vektor, WGS84) | [GeoMap — Badan Geologi ESDM](https://geologi.esdm.go.id/geomap) |
| Konsesi tambang (referensi) | [MOMI / Geoportal ESDM](https://geoportal.esdm.go.id/minerba/) |

---

## 📊 Figure Utama

| | |
|---|---|
| `fig10_prospektivitas.png` | Peta prospektivitas final (host-rock constrained) |
| `fig3_label_hostrock.png` | Validasi & penyaringan label terhadap geologi |
| `fig8_roc.png` | ROC spatial CV (naif vs jujur) |

---

## ⚠️ Keterbatasan & Pengembangan Lanjut
- Model condong ke fitur spektral → mendeteksi laterit **tersingkap**; prediksi
  potensi **di bawah tutupan** perlu penguatan fitur geologi-topografi (future work).
- Label berbasis proxy permukaan; validasi lapangan & integrasi data bor nyata
  (mis. data internal ANTAM) akan meningkatkan akurasi.
- Buffer host-rock (500 m) dapat dikalibrasi dengan data lapangan.

---

## 🤝 Kontribusi (untuk Tim)

Selamat datang, rekan tim! Ikuti panduan ringkas ini agar kolaborasi rapi.

### 1. Setup pertama kali
```bash
git clone https://github.com/USERNAME/NickelScope.git
cd NickelScope
python -m venv .venv && .venv\Scripts\activate     # Windows
pip install -r requirements.txt
```
Untuk bagian GEE: buat akun gratis di [code.earthengine.google.com](https://code.earthengine.google.com).

### 2. Alur kerja Git (branch → commit → Pull Request)
> Jangan push langsung ke `main`. Kerjakan di branch sendiri lalu buka Pull Request.
```bash
git checkout main && git pull            # ambil versi terbaru dulu
git checkout -b fitur/nama-singkat       # buat branch baru
# ... kerjakan perubahan ...
git add . && git commit -m "feat: deskripsi singkat"
git push -u origin fitur/nama-singkat    # lalu buka Pull Request di GitHub
```
**Penamaan branch:** `fitur/...`, `perbaikan/...`, `docs/...`
**Pesan commit:** awali dengan `feat:`, `fix:`, `docs:`, `refactor:`.

### 3. Konvensi folder (taruh di mana?)
| Jenis kerjaan | Lokasi | Penamaan |
|---------------|--------|----------|
| Script Google Earth Engine | `gee/` | `NN_nama.js` (berurutan) |
| Script Python (model/analisis) | `ml/` | `NN_nama.py` |
| Data input/output ringan | `data/` | `.csv`, `.tif` |
| Peta geologi / vektor | `kolaka/` | sesuai sumber |
| Figure hasil | `figures/` | dihasilkan otomatis, **jangan edit manual** |
| Dokumen/panduan | `docs/` | `.md` |

### 4. Sebelum commit — checklist
- [ ] **Jangan commit file besar mentah** (raster >10MB, scan peta) — sudah dicegah `.gitignore`.
- [ ] Kalau mengubah model/data, **regenerasi figure**: `python figures_src.py`.
- [ ] Pastikan pipeline jalan: `python ml/02_hostrock_refine.py` (tanpa error).
- [ ] Update `README.md` bila menambah script/alur baru.

### 5. Saran pembagian peran
- 🛰️ **Remote sensing / GEE** — `gee/`, akuisisi & fitur citra
- 🤖 **Data/AI** — `ml/`, model & validasi
- 🗺️ **GIS / geologi** — `kolaka/`, host-rock & validasi geologis
- 📝 **Lead / penulis** — proposal, slide, `docs/`, koordinasi PR

> Punya pertanyaan atau menemukan bug? Buka **Issue** di GitHub agar terdokumentasi.

---

## 🛡️ Catatan Data & Lisensi
Seluruh data yang digunakan bersifat **publik**. Peta geologi bersumber dari
Badan Geologi ESDM (GeoMap). Proyek ini disusun untuk keperluan ANTAM Hackathon 2026.

## 👥 Tim
*(isi nama anggota tim & institusi di sini)*
