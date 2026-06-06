/**
 * NickelScope — Step 3b: Footprint Detector & Label Helper
 * Tujuan: Bantu MENGENALI & MEMVERIFIKASI footprint tambang laterit
 *         tanpa data titik tambang sebelumnya.
 *
 * Strategi: tampilkan basemap SATELIT + "candidate mask" (laterit terbuka)
 *           supaya Anda tinggal cek-silang secara visual.
 */

// ---- AOI ----
var aoi = ee.Geometry.Rectangle([121.50, -4.35, 121.75, -3.95]);
Map.setCenter(121.61, -4.22, 12);          // zoom ke kluster Pomalaa
Map.setOptions('SATELLITE');                // <-- basemap satelit resolusi tinggi

// ---- Sentinel-2 komposit bebas-awan (musim kering) ----
function maskS2clouds(image) {
  var scl = image.select('SCL');
  var mask = scl.neq(3).and(scl.neq(8)).and(scl.neq(9)).and(scl.neq(10));
  return image.updateMask(mask).divide(10000);
}
var s2 = ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')
  .filterBounds(aoi)
  .filterDate('2023-07-01', '2023-10-31')
  .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 40))
  .map(maskS2clouds)
  .median()
  .clip(aoi);

// ---- Indeks ----
var ironOxide = s2.select('B4').divide(s2.select('B2')).rename('iron_oxide');
var ndvi      = s2.normalizedDifference(['B8','B4']).rename('ndvi');

// ---- CANDIDATE MASK: permukaan laterit terbuka ----
//   Aturan: besi tinggi DAN vegetasi rendah.
//   (Ambang bisa DISETEL — geser nilainya & lihat hasilnya.)
var IRON_THRESH = 1.6;   // naikkan = lebih ketat
var NDVI_THRESH = 0.30;  // turunkan = hanya lahan paling terbuka

var candidate = ironOxide.gt(IRON_THRESH)
                  .and(ndvi.lt(NDVI_THRESH))
                  .selfMask()
                  .rename('candidate');

// ---- Tampilan (di atas basemap satelit) ----
Map.addLayer(ironOxide, {min:1.0, max:2.5, palette:['blue','white','yellow','red']},
             'Iron Oxide Ratio', false);
Map.addLayer(candidate, {palette:['#ff00ff']}, 'KANDIDAT footprint (magenta)', true, 0.6);

/**
 * CARA VERIFIKASI (tanpa data titik sebelumnya):
 * 1. Basemap sudah SATELIT. Layer magenta = kandidat laterit terbuka.
 * 2. Geser opacity layer magenta (slider) → lihat APA yang ada di bawahnya:
 *    - Ada teras/jenjang, jalan hauling, kolam, stockpile? -> TAMBANG (positif).
 *    - Hutan/sawah/awan yang lolos filter? -> BUKAN, abaikan.
 * 3. (Disarankan) Import polygon konsesi nikel dari Geoportal ESDM sebagai
 *    asset, lalu overlay: kandidat DI DALAM konsesi = positif paling yakin.
 * 4. Tandai titik positif di pusat footprint terverifikasi (Draw a point).
 *
 * CATATAN ANTI-CIRCULARITY (penting untuk metodologi):
 *  - Iron-oxide & NDVI nanti juga dipakai sebagai FITUR model. Bila label
 *    positif 100% berasal dari ambang iron-oxide, model jadi "menghafal".
 *  - Maka: pakai candidate mask ini HANYA untuk MENEMUKAN lokasi, lalu
 *    KONFIRMASI dengan bukti independen (visual tambang / konsesi). Biarkan
 *    fitur TOPOGRAFI & GEOLOGI yang menanggung daya prediksi.
 */

// (Opsional) Overlay konsesi bila sudah punya asset shapefile:
// var konsesi = ee.FeatureCollection('users/NAMA_ANDA/konsesi_nikel');
// Map.addLayer(konsesi, {color:'cyan'}, 'Konsesi Nikel');
