# Panduan Georeferencing & Digitasi Ku (NickelScope)
### Versi anti-meleset — dengan 2 checkpoint verifikasi

> **Kenapa kemarin meleset?** Georeferencing-nya sebenarnya bagus (0.37 px), tapi
> kita **tidak memverifikasi** hasilnya terhadap citra satelit sebelum digitasi,
> dan poligon belum dicek terhadap titik tambang. Panduan ini menambahkan 2 cek itu.

---

## PERSIAPAN
1. **Project → Properties → CRS** → set **`EPSG:32751`** (WGS84 / UTM 51S).
   Ini bikin satuan kanvas = meter & menghindari kebingungan reproyeksi.

---

## BAGIAN A — Georeferencing (ulang bersih)

1. **Raster → Georeferencer.**
2. **Open Raster** → pilih JPG peta geologi asli (yang BELUM ter-georeferensi).
3. **Settings → Transformation Settings:**
   - Transformation type: **Polynomial 1**
   - Target CRS: **`EPSG:32751`**
   - Resampling: **Nearest neighbour**
   - Output raster: tentukan nama, mis. `PetaGeologi_geo.tif`
   - ✅ centang **"Load in project when done"**
4. Pasang **5 GCP** di perpotongan grid UTM (nilai bulat):

   | GCP | X (Easting) | Y (Northing) |
   |----|------------|-------------|
   | Kiri-atas | `310000` | `9550000` |
   | Kanan-atas | `490000` | `9550000` |
   | Kiri-bawah | `310000` | `9500000` |
   | Kanan-bawah | `490000` | `9500000` |
   | Tengah | `400000` | `9530000` |

   > Klik tepat di perpotongan garis Easting × Northing. **Zoom in** saat klik agar presisi.
5. Pastikan **Mean error < 2 px** (kemarin 0.37 — target serupa).
6. Klik **Start Georeferencing** (▶️). GeoTIFF hasil otomatis masuk kanvas.

---

## ✅ CHECKPOINT 1 — Verifikasi vs satelit (WAJIB, ini yang kemarin terlewat!)

1. Tambahkan basemap satelit: **Web → QuickMapServices → Google Satellite**
   (atau NextGIS QMS → cari "Google Satellite"). Taruh di **bawah** peta geologi.
2. Turunkan **opacity peta geologi ke ~50%** (klik kanan layer → Properties → Transparency).
3. **Cek garis pantai & pulau** (P. Lambasina, P. Padamarang, Teluk Kolaka):
   - ✅ **Berimpit** dengan satelit → georef OK, lanjut ke Bagian B.
   - ❌ **Meleset > ~500 m** → lihat kotak TROUBLESHOOTING di bawah.

> Jangan lanjut digitasi sebelum garis pantai berimpit. Ini akar masalah kemarin.

---

## BAGIAN B — Digitasi poligon Ku

1. **Layer → Create Layer → New Shapefile Layer:**
   - Geometry: **Polygon**
   - CRS: **`EPSG:32751`** (samakan dengan project)
   - Nama: `ultramafic_ku`
2. Pilih layer → **Toggle Editing** (pensil) → **Add Polygon Feature**.
3. **Trace semua area `Ku`** yang beririsan AOI (Kolaka–Pomalaa, sisi barat peta).
   Pakai peta geologi (opacity 50%) sebagai panduan; aktifkan **Snapping**.
4. Klik kanan untuk menutup poligon; ulangi untuk tiap badan Ku terpisah.
5. **Save** (Ctrl+S), lalu **Toggle Editing** off.

---

## ✅ CHECKPOINT 2 — Ku HARUS menutupi titik tambang (WAJIB!)

1. Tambah titik label: **Layer → Add Delimited Text Layer** → `nickelscope_labels.csv`
   - X = `lon`, Y = `lat`, **Geometry CRS = `EPSG:4326`**.
2. Beri warna titik (mis. positif = merah).
3. **Cek visual:** apakah poligon Ku menutupi titik-titik positif Pomalaa?
   - ✅ **Ya, semua positif di dalam Ku** → sempurna, lanjut export.
   - ❌ **Ada positif di luar Ku** → **perluas poligon** ke area itu
     (pastikan di peta geologi area itu memang Ku / laterit di atas ultramafik).

> Target: ~100% titik positif berada di dalam poligon Ku. Kemarin cuma 55%.

---

## BAGIAN C — Export & Upload ke GEE (hindari masalah CRS)

1. Klik kanan layer `ultramafic_ku` → **Export → Save Features As:**
   - Format: **ESRI Shapefile**
   - **CRS: ubah ke `EPSG:4326`** ← penting! Hindari ambiguitas UTM saat upload.
   - Simpan, mis. `ultramafic_ku_4326.shp`
2. **Zip** semua file hasil (.shp, .shx, .dbf, .prj).
3. GEE: **Assets → New → Shape files (.zip)** → upload → jadi FeatureCollection.
4. Copy path asset → tempel di [gee/06_hostrock_features.js](../gee/06_hostrock_features.js)
   pada `var ultramafic = ...`.

---

## ✅ CHECKPOINT 3 — Verifikasi akhir di GEE
Jalankan script 06 → cek layer "Ultramafik (Ku)" menutupi kluster tambang.
Cek juga statistik: titik positif di dalam ultramafik harus mendekati 100%.

---

## 🔧 TROUBLESHOOTING — kalau Checkpoint 1 masih meleset

| Gejala | Kemungkinan sebab | Solusi |
|--------|-------------------|--------|
| Meleset **sistematis** ~100–300 m, arah konsisten | **Beda datum** (peta lama = ID74/datum lama, bukan WGS84) | Untuk akurasi lebih baik, georef ulang pakai **fitur nyata**: pasang GCP di **ujung tanjung, mulut sungai, ujung pulau** yang dikenali di peta DAN di satelit (image-to-image). |
| Meleset **besar/acak** | Salah ketik GCP / klik tidak presisi | Cek tabel GCP, perbaiki residual yang melonjak; klik ulang dengan zoom. |
| Poligon benar di QGIS tapi meleset di GEE | **CRS hilang saat upload** | Pastikan export ke **EPSG:4326** + .prj ikut ter-zip. |

### Cara georef berbasis fitur (kalau datum bikin meleset)
1. Di Georeferencer, **From Map Canvas** (ikon) → klik fitur di satelit untuk ambil koordinatnya.
2. Pasang 4–6 GCP di titik-titik pantai/pulau yang jelas di kedua peta.
3. Ini menyelaraskan langsung ke realita satelit → overlay paling pas untuk analisis.
