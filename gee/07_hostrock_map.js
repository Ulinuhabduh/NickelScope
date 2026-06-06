/**
 * NickelScope — Step 7: Peta Prospektivitas HOST-ROCK CONSTRAINED (final, jujur)
 * Peta akhir = favorability ML  ×  host-rock mask (ultramafik resmi + buffer).
 *
 * PRASYARAT:
 *  - Upload 'kolaka/ultramafic_kolaka.zip' ke GEE (Assets -> New -> Shape files).
 *  - Asset titik label 'nickelscope_labels' sudah ada.
 */

var aoi = ee.Geometry.Rectangle([121.50, -4.35, 121.75, -3.95]);
Map.setCenter(121.61, -4.22, 11);
Map.setOptions('SATELLITE');

// ---- Ultramafik resmi (GeoMap 1:100k, WGS84 -> pasti align) ----
var ultramafic = ee.FeatureCollection('projects/robotic-goal-480609-j0/assets/ultramafic_kolaka');
var BUFFER = 500;  // meter — tutupan laterit di atas ultramafik
var domain = ultramafic.geometry().buffer(BUFFER);          // domain host-rock
var domainMask = ee.Image.constant(1).clip(domain);

// ---- Titik label, disaring ke domain host-rock ----
var labelsRaw = ee.FeatureCollection('projects/robotic-goal-480609-j0/assets/nickelscope_labels');
var labels = labelsRaw.map(function(f){
  var lon = ee.Number.parse(ee.Algorithms.String(f.get('lon')));
  var lat = ee.Number.parse(ee.Algorithms.String(f.get('lat')));
  return ee.Feature(ee.Geometry.Point([lon, lat]), {label: f.get('label')});
}).filterBounds(domain);   // <- hanya label di host-rock (buang false-positive sedimen)

// ---- Feature stack (8 fitur) ----
function maskS2(image){
  var scl=image.select('SCL');
  var m=scl.neq(3).and(scl.neq(8)).and(scl.neq(9)).and(scl.neq(10));
  return image.updateMask(m).divide(10000);
}
var s2=ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')
  .filterBounds(aoi).filterDate('2023-07-01','2023-10-31')
  .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE',40)).map(maskS2).median().clip(aoi);
var iron=s2.select('B4').divide(s2.select('B2')).rename('iron_oxide');
var ferr=s2.select('B11').divide(s2.select('B8')).rename('ferrous');
var clay=s2.select('B11').divide(s2.select('B12')).rename('clay');
var ndvi=s2.normalizedDifference(['B8','B4']).rename('ndvi');
var dem=ee.Image('USGS/SRTMGL1_003').clip(aoi);
var slope=ee.Terrain.slope(dem).rename('slope');
var curv=dem.convolve(ee.Kernel.laplacian8()).rename('curvature');
var upa=ee.Image('MERIT/Hydro/v1_0_1').select('upa').clip(aoi);
var twi=upa.multiply(1e6).divide(slope.multiply(Math.PI/180).tan().max(0.001)).log().rename('twi');
var BANDS=['iron_oxide','ferrous','clay','ndvi','elevation','slope','curvature','twi'];
var stack=iron.addBands(ferr).addBands(clay).addBands(ndvi)
   .addBands(dem.rename('elevation')).addBands(slope).addBands(curv).addBands(twi);

// ---- Train RF di label in-domain, klasifikasi, lalu MASK ke host-rock ----
var training=stack.sampleRegions({collection:labels, properties:['label'], scale:20});
var clf=ee.Classifier.smileRandomForest(400).setOutputMode('PROBABILITY')
        .train({features:training, classProperty:'label', inputProperties:BANDS});
var prospect=stack.classify(clf).rename('prospectivity')
        .updateMask(domainMask)        // <- HANYA di host-rock valid
        .clip(aoi);

// ---- Visualisasi ----
var palette=['000080','0000ff','00ffff','ffff00','ff8000','ff0000'];
Map.addLayer(ultramafic,{color:'white'},'Ultramafik (Ku) resmi',false);
Map.addLayer(prospect,{min:0,max:1,palette:palette},'Prospektivitas (host-rock constrained)');
Map.addLayer(prospect.gt(0.8).selfMask(),{palette:['#00ff00']},'Target prioritas (>0.8)',false);

// ---- Export ----
Export.image.toDrive({image:prospect, description:'nickelscope_prospectivity_hostrock',
  region:aoi, scale:20, maxPixels:1e9, fileFormat:'GeoTIFF'});

/**
 * Inilah peta FINAL yang jujur:
 *  - Prediksi HANYA muncul di host-rock ultramafik valid (+buffer laterit).
 *  - Tidak ada lagi bocoran di laut / sedimen / permukiman.
 *  - Dilatih pada label yang sudah dibersihkan secara geologis.
 */
