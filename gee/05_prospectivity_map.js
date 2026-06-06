/**
 * NickelScope — Step 5 (Fase 4): Peta Prospektivitas (wall-to-wall)
 * Latih Random Forest di GEE -> klasifikasi seluruh AOI -> peta probabilitas.
 * Validasi rigor (spatial CV) sudah dilakukan di Python; ini untuk RENDER PETA.
 */

// ---- AOI ----
var aoi = ee.Geometry.Rectangle([121.50, -4.35, 121.75, -3.95]);
Map.setCenter(121.61, -4.22, 11);

// ---- Titik label (path asset Anda) ----
var labelsRaw = ee.FeatureCollection('projects/robotic-goal-480609-j0/assets/nickelscope_labels');
var labels = labelsRaw.map(function(f){
  var lon = ee.Number.parse(ee.Algorithms.String(f.get('lon')));
  var lat = ee.Number.parse(ee.Algorithms.String(f.get('lat')));
  return ee.Feature(ee.Geometry.Point([lon, lat]), {label: f.get('label')});
});

// =====================================================
// FEATURE STACK (sama dgn Fase 2)
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

var iron_oxide = s2.select('B4').divide(s2.select('B2')).rename('iron_oxide');
var ferrous    = s2.select('B11').divide(s2.select('B8')).rename('ferrous');
var clay       = s2.select('B11').divide(s2.select('B12')).rename('clay');
var ndvi       = s2.normalizedDifference(['B8','B4']).rename('ndvi');

var dem   = ee.Image('USGS/SRTMGL1_003').clip(aoi);
var elev  = dem.rename('elevation');
var slope = ee.Terrain.slope(dem).rename('slope');
var curv  = dem.convolve(ee.Kernel.laplacian8()).rename('curvature');
var upa   = ee.Image('MERIT/Hydro/v1_0_1').select('upa').clip(aoi);
var twi   = upa.multiply(1e6).divide(slope.multiply(Math.PI/180).tan().max(0.001)).log().rename('twi');

var BANDS = ['iron_oxide','ferrous','clay','ndvi','elevation','slope','curvature','twi'];
var stack = iron_oxide.addBands(ferrous).addBands(clay).addBands(ndvi)
              .addBands(elev).addBands(slope).addBands(curv).addBands(twi);

// =====================================================
// TRAIN RF (mode PROBABILITY) + KLASIFIKASI
// =====================================================
var training = stack.sampleRegions({collection: labels, properties:['label'], scale:20});
var clf = ee.Classifier.smileRandomForest(400)
            .setOutputMode('PROBABILITY')
            .train({features: training, classProperty:'label', inputProperties: BANDS});

var prospect = stack.classify(clf).rename('prospectivity').clip(aoi);

// =====================================================
// HOST-ROCK MASK (opsional, Fase 1b) — bikin peta JUJUR
// Gambar geometry import 'ultramafic' (Polygon) menutupi sabuk ophiolite,
// lalu HILANGKAN komentar baris di bawah supaya prediksi hanya di ultramafik.
// =====================================================
// prospect = prospect.updateMask(ee.Image.constant(0).paint(ultramafic,1));

// =====================================================
// VISUALISASI
// =====================================================
var palette = ['000080','0000ff','00ffff','ffff00','ff8000','ff0000']; // biru->merah
Map.addLayer(prospect, {min:0, max:1, palette:palette}, 'Peta Prospektivitas (0-1)');
Map.addLayer(prospect.gt(0.8).selfMask(), {palette:['#00ff00']},
             'Target prioritas (prob > 0.8)', false);
Map.addLayer(labels.filter(ee.Filter.eq('label',1)), {color:'black'}, 'Titik positif', false);

// =====================================================
// EXPORT peta (GeoTIFF) ke Drive
// =====================================================
Export.image.toDrive({
  image: prospect, description: 'nickelscope_prospectivity',
  region: aoi, scale: 20, maxPixels: 1e9, fileFormat: 'GeoTIFF'
});

/**
 * BACA PETA INI DGN KRITIS:
 *  - Tanpa host-rock mask, zona merah cenderung = laterit yg SUDAH tersingkap
 *    (efek circularity). Itu wajar untuk v1.
 *  - Nyalakan host-rock mask (ultramafik) agar prediksi tidak "bocor" ke
 *    area non-ultramafik (mis. permukiman/pantai) -> peta lebih jujur.
 *  - Langkah lanjut: tambah fitur 'jarak ke ultramafik' & varian model
 *    prospektivitas (topografi+geologi) untuk potensi DI BAWAH tutupan.
 */
