/**
 * NickelScope — Step 4 (Fase 2): Feature Engineering
 * Ekstrak fitur prediktor di tiap titik label -> features.csv (siap ML).
 *
 * PRASYARAT: upload 'nickelscope_labels.csv' sebagai GEE asset.
 *   Assets -> New -> CSV (table upload). Set kolom X='lon', Y='lat'.
 *   Lalu ganti path di bawah dengan path asset Anda.
 */

// ---- AOI ----
var aoi = ee.Geometry.Rectangle([121.50, -4.35, 121.75, -3.95]);

// ---- Titik label (GANTI path asset ini) ----
// Bangun ULANG geometri titik dari kolom lon/lat (anti-masalah "geometri kosong"
// saat upload CSV tidak men-set kolom X/Y).
var labelsRaw = ee.FeatureCollection('projects/robotic-goal-480609-j0/assets/nickelscope_labels');
// (alternatif lama: 'users/USERNAME/nickelscope_labels')

var labels = labelsRaw.map(function(f){
  var lon = ee.Number.parse(ee.Algorithms.String(f.get('lon')));
  var lat = ee.Number.parse(ee.Algorithms.String(f.get('lat')));
  return ee.Feature(ee.Geometry.Point([lon, lat]), {label: f.get('label')});
});

// ---- DIAGNOSTIK (lihat di console) ----
print('Jumlah titik mentah:', labelsRaw.size());     // harus 650
print('Contoh titik (cek geometry):', labels.first()); // harus punya Point geometry

// =====================================================
// 1) SENTINEL-2 — komposit bebas-awan (musim kering)
// =====================================================
function maskS2clouds(image){
  var scl = image.select('SCL');
  var mask = scl.neq(3).and(scl.neq(8)).and(scl.neq(9)).and(scl.neq(10));
  return image.updateMask(mask).divide(10000);
}
var s2 = ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')
  .filterBounds(aoi).filterDate('2023-07-01','2023-10-31')
  .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE',40))
  .map(maskS2clouds).median().clip(aoi);

// ---- Indeks spektral (proxy mineralogi) ----
var iron_oxide = s2.select('B4').divide(s2.select('B2')).rename('iron_oxide'); // Fe-oksida
var ferrous    = s2.select('B11').divide(s2.select('B8')).rename('ferrous');   // mineral ferro
var clay       = s2.select('B11').divide(s2.select('B12')).rename('clay');     // lempung/alterasi
var ndvi       = s2.normalizedDifference(['B8','B4']).rename('ndvi');           // vegetasi

// =====================================================
// 2) TOPOGRAFI (SRTM 30 m)
// =====================================================
var dem     = ee.Image('USGS/SRTMGL1_003').clip(aoi);
var elev    = dem.rename('elevation');
var slope   = ee.Terrain.slope(dem).rename('slope');               // derajat
var curv    = dem.convolve(ee.Kernel.laplacian8()).rename('curvature'); // kelengkungan

// ---- TWI (Topographic Wetness Index) via MERIT Hydro ----
var upa      = ee.Image('MERIT/Hydro/v1_0_1').select('upa').clip(aoi); // km^2
var tanSlope = slope.multiply(Math.PI/180).tan().max(0.001);          // hindari /0
var twi      = upa.multiply(1e6).divide(tanSlope).log().rename('twi');

// =====================================================
// 3) STACK FITUR
// =====================================================
var stack = iron_oxide.addBands(ferrous).addBands(clay).addBands(ndvi)
              .addBands(elev).addBands(slope).addBands(curv).addBands(twi);

// (CATATAN) Fitur GEOLOGI 'jarak ke ultramafik' belum ada di sini -->
//   ditambahkan setelah layer host-rock (peta geologi) disiapkan (Fase 1b).

// =====================================================
// 4) SAMPLING di titik label
// =====================================================
var samples = stack.sampleRegions({
  collection: labels,
  properties: ['label'],
  scale: 20,
  geometries: true
}).map(function(f){
  var c = f.geometry().coordinates();
  return f.set('lon', c.get(0)).set('lat', c.get(1));
});

print('Jumlah sampel:', samples.size());
print('Contoh 5 baris fitur:', samples.limit(5));

// =====================================================
// 5) EXPORT features.csv
// =====================================================
Export.table.toDrive({
  collection: samples,
  description: 'nickelscope_features',
  fileFormat: 'CSV',
  selectors: ['lon','lat','iron_oxide','ferrous','clay','ndvi',
              'elevation','slope','curvature','twi','label']
});

/**
 * SETELAH EXPORT:
 *  - Cek apakah ada baris dgn nilai kosong (titik jatuh di piksel ber-awan).
 *    Kalau ada, buang baris itu di Python (dropna) atau perlebar rentang tanggal.
 *  - INGAT anti-circularity: iron_oxide kuat, tapi jangan biarkan ia satu-satunya
 *    penentu. Laporkan feature importance jujur; biarkan slope/twi/curvature/
 *    elevation & (nanti) geologi ikut menanggung prediksi.
 */
