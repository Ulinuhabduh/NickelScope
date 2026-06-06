/**
 * NickelScope — Step 6 (Fase 1b): Host-Rock Geology
 * - Tambah fitur GEOLOGI 'dist_um' (jarak ke ultramafik)
 * - Re-extract fitur di titik label -> features_v2.csv (untuk retrain)
 * - Preview peta yang sudah di-MASK ke ultramafik (lebih jujur)
 *
 * PRASYARAT: upload poligon 'Ku' (ultramafik) hasil digitasi sebagai asset.
 *   Assets -> New -> Shape files (.zip)  ATAU gambar geometry import 'ultramafic'.
 */

// ---- AOI ----
var aoi = ee.Geometry.Rectangle([121.50, -4.35, 121.75, -3.95]);
Map.setCenter(121.61, -4.22, 11);

// ---- Ultramafik (Ku) ----
// OPSI A (DISARANKAN): gambar polygon 'ultramafic' langsung di GEE (Geometry Imports),
//   jiplak sabuk ultramafik di atas basemap SATELIT -> pasti align ke realita.
// OPSI B: pakai asset shapefile hasil digitasi QGIS (uncomment & ganti path).
Map.setOptions('SATELLITE');
var ultramaficFC = ee.FeatureCollection(ee.Feature(ultramafic));   // <- dari polygon gambar
// var ultramaficFC = ee.FeatureCollection('projects/ee-USERNAME/assets/ultramafic_ku'); // OPSI B
Map.addLayer(ultramaficFC, {color:'purple'}, 'Ultramafik (Ku)', true, 0.4);

// ---- Titik label ----
var labelsRaw = ee.FeatureCollection('projects/ee-USERNAME/assets/nickelscope_labels');
var labels = labelsRaw.map(function(f){
  var lon = ee.Number.parse(ee.Algorithms.String(f.get('lon')));
  var lat = ee.Number.parse(ee.Algorithms.String(f.get('lat')));
  return ee.Feature(ee.Geometry.Point([lon, lat]), {label: f.get('label')});
});

// =====================================================
// FEATURE STACK (8 fitur lama + 1 fitur geologi)
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

// ---- FITUR GEOLOGI: jarak ke ultramafik (meter) ----
// 0 di dalam Ku, makin besar makin jauh (dibatasi 50 km).
var inside  = ee.Image().byte().paint(ultramaficFC, 1).unmask(0);
var distRaw = ultramaficFC.distance(50000, 100).unmask(50000);
var dist_um = distRaw.where(inside.eq(1), 0).rename('dist_um').clip(aoi);

var BANDS = ['iron_oxide','ferrous','clay','ndvi','elevation','slope','curvature','twi','dist_um'];
var stack = iron_oxide.addBands(ferrous).addBands(clay).addBands(ndvi)
              .addBands(elev).addBands(slope).addBands(curv).addBands(twi).addBands(dist_um);

// =====================================================
// RE-EXTRACT fitur di titik label -> features_v2.csv
// =====================================================
var samples = stack.sampleRegions({collection: labels, properties:['label'], scale:20, geometries:true})
  .map(function(f){ var c=f.geometry().coordinates();
                    return f.set('lon',c.get(0)).set('lat',c.get(1)); });
print('Jumlah sampel v2:', samples.size());
Export.table.toDrive({
  collection: samples, description:'nickelscope_features_v2', fileFormat:'CSV',
  selectors: ['lon','lat'].concat(BANDS).concat(['label'])
});

// =====================================================
// PREVIEW: peta lama di-MASK ke ultramafik (host-rock honest)
// (latih RF cepat di GEE hanya untuk lihat efek masking)
// =====================================================
var training = stack.sampleRegions({collection: labels, properties:['label'], scale:20});
var clf = ee.Classifier.smileRandomForest(400).setOutputMode('PROBABILITY')
            .train({features: training, classProperty:'label', inputProperties: BANDS});
var prospect = stack.classify(clf).rename('prospectivity').clip(aoi);

// MASK: hanya tampilkan prediksi di ultramafik (buang laut/non-ultramafik)
var prospectMasked = prospect.updateMask(inside.eq(1));

var palette = ['000080','0000ff','00ffff','ffff00','ff8000','ff0000'];
Map.addLayer(prospect,       {min:0,max:1,palette:palette}, 'Prospektivitas (tanpa mask)', false);
Map.addLayer(prospectMasked, {min:0,max:1,palette:palette}, 'Prospektivitas (MASK ultramafik)', true);

/**
 * Bandingkan 2 layer:
 *  - "tanpa mask": ada bocoran di laut/permukiman (false positive).
 *  - "MASK ultramafik": bersih, hanya di host-rock yg valid -> JUJUR.
 * Lalu retrain di Python pakai features_v2.csv (lihat 9 fitur, cek importance
 * dist_um) untuk perbandingan model.
 */
