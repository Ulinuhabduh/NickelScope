# NickelScope 🛰️⛏️
### AI-GIS Prospectivity Mapping untuk Eksplorasi Nikel Laterit Berbasis Penginderaan Jauh

**Lomba:** ANTAM Hackathon 2026 — Young Mining Innovators
**Tema:** 1. Eksplorasi
**Komoditas:** Nikel Laterit (prioritas utama ANTAM)
**Tim:** Geologi/Tambang + Data/AI

---

## Ringkasan Satu Kalimat
> NickelScope adalah sistem AI-GIS yang memetakan **probabilitas keterdapatan nikel laterit** dari fusi citra satelit, DEM, dan peta geologi — menghasilkan **peta target bor prioritas** sekaligus **layer risiko ESG** untuk mengurangi biaya, waktu, dan dampak lingkungan eksplorasi.

---

## 1. Judul & Tema
- **Judul:** NickelScope — AI-GIS Prospectivity Mapping untuk Eksplorasi Nikel Laterit Berbasis Penginderaan Jauh
- **Tema utama:** Eksplorasi
- **Integrasi wajib:**
  - **AI** → model Machine Learning (Random Forest/XGBoost) untuk klasifikasi prospektivitas
  - **GIS** → analisis spasial multi-layer, WebGIS interaktif
  - **Data Analytics** → feature engineering geologi, scoring, peta ketidakpastian
  - **ESG/Safety/Risk** → layer no-go zone, risiko akses lapangan, peta ketidakpastian keputusan

---

## 2. Problem Statement
**Masalah utama:** Eksplorasi nikel laterit konvensional mengandalkan pengeboran intensif yang **mahal, lambat, dan sering "buta"** — banyak lubang bor jatuh di area non-prospektif.

**Urgensi & dampak:**
- **Biaya:** Satu titik bor eksplorasi bisa menelan puluhan–ratusan juta rupiah; pengeboran tidak terarah = pemborosan besar.
- **Waktu:** Siklus eksplorasi panjang → memperlambat konversi sumber daya jadi cadangan.
- **Risiko/ESG:** Pengeboran serampangan di area sensitif (hutan lindung, sungai, lereng curam) menambah jejak lingkungan & risiko K3.

**Pernyataan masalah:** *Bagaimana mengarahkan kegiatan eksplorasi & pengeboran nikel laterit secara lebih cerdas, hemat, dan bertanggung jawab menggunakan data yang tersedia secara publik — sebelum alat berat masuk ke lapangan?*

---

## 3. Cakupan Studi Kasus
- **Lokasi studi kasus (TERKUNCI):** **Sabuk Pomalaa–Kolaka, Sulawesi Tenggara** — aset nikel andalan ANTAM, bagian East Sulawesi Ophiolite Belt. **Data 100% publik**, *bukan* data internal ANTAM.
  - **AOI bounding box:** Lat **-4.35° s/d -3.95° S**, Lon **121.50° s/d 121.75° E** (~28 km × 44 km)
  - Mencakup distrik tambang Pomalaa (Tambang Utara & Selatan) hingga selatan Kolaka.
- **Komoditas/proses:** Nikel laterit (host: batuan ultramafik/peridotit yang terlapukkan).
- **Batasan asumsi:**
  - Model berbasis proxy permukaan (remote sensing + topografi), bukan pengganti pengeboran — output = *prioritisasi*, bukan kepastian.
  - Label training berasal dari okurensi nikel terpublikasi / peta geologi, dengan ketidakpastian yang didokumentasikan.
- **Alasan pemilihan:** Nikel = komoditas prioritas ANTAM & rantai nilai EV battery; data laterit mudah dikenali dari permukaan (cocok remote sensing).

---

## 4. Data & Metode

### Data (semua gratis & legal)
| Data | Sumber | Kegunaan |
|------|--------|----------|
| Citra Sentinel-2 (10–20 m) | Google Earth Engine / Copernicus | Indeks besi/alterasi, vegetasi |
| DEM (DEMNAS 8 m / SRTM 30 m) | Badan Informasi Geospasial / USGS | Slope, elevasi, curvature, TWI, drainase |
| Peta Geologi 1:250.000 | Badan Geologi ESDM | Litologi ultramafik sebagai host |
| ASTER (opsional) | NASA EarthData | Pemetaan mineral lanjutan |
| Titik okurensi nikel | Publikasi ilmiah / peta sebaran | Label training (positif) |

### Feature Engineering — *di sinilah keunggulan domain geologi tim masuk* 🧠
- **Iron Oxide Ratio** (B4/B2 Sentinel-2) → laterit kaya Fe-oksida
- **NDVI** → tutupan vegetasi (proxy pelapukan/tanah)
- **Slope & Curvature** → laterit terbentuk & terawetkan di permukaan landai/stabil
- **TWI (Topographic Wetness Index)** → kontrol pelindian (leaching) Ni
- **Jarak ke litologi ultramafik** → kedekatan ke batuan induk
- **Densitas lineament/struktur** → jalur pelapukan & akumulasi

### Metode
1. **Baseline:** Weights of Evidence (WoE) — metode prospektivitas klasik, mudah dijelaskan ke juri.
2. **Model utama:** Random Forest / XGBoost (supervised), atau ensemble.
3. **Label:** positif = okurensi diketahui; negatif = area non-prospektif (sampling acak berbasis buffer).
4. **Validasi:** spatial train/test split, ROC-AUC, success-rate curve.
5. **Uncertainty map:** variance/entropy prediksi → komunikasikan tingkat keyakinan (manajemen risiko keputusan).

---

## 5. Target Prototype
**WebGIS Dashboard interaktif "NickelScope"** (Streamlit + Folium/Leaflet atau Google Earth Engine App):
- 🗺️ **Peta probabilitas prospektivitas** (0–1, gradasi warna)
- 🚫 **Layer No-Go ESG** (hutan lindung, sungai, pemukiman, lereng berbahaya)
- 📊 **Tabel ranking target bor prioritas** (koordinat + skor + tingkat keyakinan)
- ⚠️ **Peta ketidakpastian** (uncertainty)
- 📄 **Data Quality Report** otomatis

---

## 6. Dampak & Manfaat
- 💰 **Cost saving:** Fokus bor ke zona high-probability → potensi pengurangan area bor X% (estimasi dari success-rate curve).
- ⏱️ **Efisiensi waktu:** Persempit target sebelum mobilisasi alat berat.
- 🌱 **ESG:** Layer no-go mengurangi gangguan di area sensitif & jejak eksplorasi.
- 🦺 **Safety/Risk:** Hindari area akses berbahaya (lereng curam), peta ketidakpastian → keputusan sadar risiko.
- 📈 **Nilai tambah:** De-risking keputusan eksplorasi, mempercepat pipeline sumber daya → cadangan.

---

## 7. Feasibility & Implementasi
- **Sumber daya:** Semua data publik gratis; stack open-source (Python, GEE, scikit-learn, Streamlit, QGIS) → sesuai TOR.
- **Risiko implementasi:** kurva belajar GEE (terkelola, banyak tutorial); kualitas label (didokumentasikan & divalidasi).
- **Roadmap pengembangan lanjut:**
  1. Integrasi data bor internal ANTAM (retrain dengan label nyata)
  2. Validasi lapangan & kalibrasi model
  3. Ekspansi multi-komoditas (emas, bauksit, mineral kritis)
  4. Integrasi ke sistem perencanaan eksplorasi ANTAM

---

## 🎤 Storyline Pitch (2 menit)
1. **Hook (15 dtk):** "Setiap lubang bor yang kering = ratusan juta rupiah & jejak lingkungan yang hangus. Bagaimana kalau AI bisa menunjukkan ke mana harus mengebor — sebelum alat berat masuk?"
2. **Problem (20 dtk):** Eksplorasi nikel = mahal, lambat, banyak bor buta.
3. **Solusi (30 dtk):** NickelScope — fusi citra satelit + DEM + geologi + AI → peta target prioritas.
4. **Demo (40 dtk):** Tunjukkan peta prospektivitas berwarna + layer no-go ESG + ranking target.
5. **Impact & Vision (15 dtk):** Hemat biaya, ramah lingkungan, siap diintegrasi ke alur eksplorasi ANTAM.

---

## ✅ Pemetaan ke Kriteria Penjurian
| Kriteria | Bobot | Bagaimana NickelScope menang |
|----------|:---:|------------------------------|
| Problem & metodologi | 25% | Masalah nyata komoditas prioritas + metode WoE+ML teruji |
| Kreativitas & teknologi | 25% | Fusi geospasial + ML + feature engineering geologi |
| Kualitas prototype | 25% | WebGIS interaktif, peta visual "wow", demoable |
| Dampak & implementasi | 15% | Cost saving terukur + roadmap integrasi ANTAM |
| Presentasi | 10% | Storyline kuat + demo peta dramatis |
