/**
 * NickelScope — Step 3: AOI Explorer & Label-Gathering Aid
 * Area: Pomalaa–Kolaka, Sulawesi Tenggara
 * Platform: Google Earth Engine Code Editor (code.earthengine.google.com)
 *
 * Tujuan: Tampilkan citra bebas-awan + indeks besi (iron oxide) supaya
 *         footprint tambang laterit nikel terlihat jelas → mudah didigitasi
 *         sebagai LABEL POSITIF.
 */

// 1) AREA OF INTEREST (Pomalaa–Kolaka)
var aoi = ee.Geometry.Rectangle([121.50, -4.35, 121.75, -3.95]);
// Pakai setCenter(lon, lat, zoom) — hindari Map.centerObject() yang pada
// sebagian versi GEE memicu error "Geometry.centroid argument 'maxError'".
Map.setCenter(121.625, -4.15, 11);   // titik tengah AOI
Map.addLayer(aoi, {color: 'red'}, 'AOI Pomalaa-Kolaka', false);

// 2) SENTINEL-2 — komposit median bebas-awan (musim kering: Jul–Okt)
function maskS2clouds(image) {
  var scl = image.select('SCL');
  // buang: cloud shadow(3), cloud med/high(8,9), cirrus(10)
  var mask = scl.neq(3).and(scl.neq(8)).and(scl.neq(9)).and(scl.neq(10));
  return image.updateMask(mask).divide(10000);
}

var s2 = ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')
  .filterBounds(aoi)
  .filterDate('2023-07-01', '2023-10-31')   // musim kering Sultra = sedikit awan
  .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 40))
  .map(maskS2clouds)
  .median()
  .clip(aoi);

// 3) TRUE COLOR (referensi visual)
Map.addLayer(s2, {bands: ['B4','B3','B2'], min: 0, max: 0.3}, 'True Color', false);

// 4) FALSE COLOR (vegetasi merah, tanah terbuka terlihat jelas)
Map.addLayer(s2, {bands: ['B8','B4','B3'], min: 0, max: 0.4}, 'False Color', false);

// 5) IRON OXIDE RATIO (B4/B2) — laterit kaya Fe = nilai TINGGI
//    Inilah penanda utama footprint tambang/singkapan laterit.
var ironOxide = s2.select('B4').divide(s2.select('B2')).rename('iron_oxide');
Map.addLayer(ironOxide, {min: 1.0, max: 2.5, palette: ['blue','white','yellow','red']},
             'Iron Oxide Ratio (laterit = merah)', true);

// 6) NDVI (vegetasi) — area tambang aktif = NDVI rendah (lahan terbuka)
var ndvi = s2.normalizedDifference(['B8','B4']).rename('ndvi');
Map.addLayer(ndvi, {min: -0.1, max: 0.8, palette: ['red','yellow','green']}, 'NDVI', false);

/**
 * CARA PAKAI untuk mengumpulkan LABEL POSITIF:
 * 1. Jalankan script → nyalakan layer "Iron Oxide Ratio".
 * 2. Cari kluster MERAH (Fe tinggi) + NDVI rendah = footprint tambang laterit.
 *    Silang-cek dengan True Color (warna coklat-kemerahan, lahan terbuka).
 * 3. Pakai tool "Draw a point" (panel Geometry Imports) → buat layer 'positif'.
 *    Klik tiap pusat footprint tambang → titik positif.
 * 4. Untuk LABEL NEGATIF: buat layer 'negatif', taruh titik di area
 *    vegetasi rapat / non-ultramafik (akan dipertegas dgn peta geologi).
 * 5. Export titik: Tabel → Export.table.toDrive() sebagai CSV.
 *
 * CATATAN: Tanggal & %awan bisa disesuaikan kalau komposit masih berawan.
 */
