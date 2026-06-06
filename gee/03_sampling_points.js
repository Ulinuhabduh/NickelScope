/**
 * NickelScope — Step 3c: Sampling Titik dari Poligon (Positif & Negatif)
 *
 * Alur: gambar POLIGON footprint (bukan klik titik satu-satu),
 *       lalu GEE menabur titik acak otomatis di dalamnya secara seimbang.
 *
 * CARA PAKAI:
 *  1. Di panel "Geometry Imports", buat 2 layer:
 *       - 'posPoly'  -> tipe Polygon, warna bebas. Gambar mengelilingi
 *                       SETIAP footprint tambang TERVERIFIKASI (boleh banyak poligon).
 *       - 'negPoly'  -> tipe Polygon. Gambar di area NON-prospektif
 *                       (hutan rapat / non-ultramafik / jauh dari tambang).
 *  2. Atur jumlah titik di bawah, lalu Run.
 *  3. Klik task di tab "Tasks" untuk export CSV ke Google Drive.
 */

// ---- Parameter sampling (SETEL sesuai kebutuhan) ----
var N_POS  = 300;   // total titik positif di SELURUH posPoly
var N_NEG  = 350;   // total titik negatif (sedikit lebih banyak itu wajar)
var SEED   = 42;    // reproducibility

// ---- Tabur titik acak di dalam poligon ----
// randomPoints menyebar merata; jumlah proporsional thd luas tiap poligon,
// jadi tambang besar otomatis dapat lebih banyak titik TANPA mendominasi ekstrem.
var posPts = ee.FeatureCollection.randomPoints(posPoly, N_POS, SEED)
              .map(function(f){ return f.set('label', 1); });
var negPts = ee.FeatureCollection.randomPoints(negPoly, N_NEG, SEED + 1)
              .map(function(f){ return f.set('label', 0); });

var labels = posPts.merge(negPts);

// ---- Visual cek ----
Map.setOptions('SATELLITE');
Map.centerObject(posPoly, 12);
Map.addLayer(posPoly, {color:'cyan'},    'Poligon Positif', true, 0.3);
Map.addLayer(negPoly, {color:'yellow'},  'Poligon Negatif', true, 0.3);
Map.addLayer(posPts,  {color:'red'},     'Titik Positif');
Map.addLayer(negPts,  {color:'blue'},    'Titik Negatif');
print('Jumlah titik positif:', posPts.size());
print('Jumlah titik negatif:', negPts.size());

// ---- Export ke CSV (lat, lon, label) ----
var labelsLL = labels.map(function(f){
  var c = f.geometry().coordinates();
  return f.set('lon', c.get(0)).set('lat', c.get(1));
});
Export.table.toDrive({
  collection: labelsLL,
  description: 'nickelscope_labels',
  fileFormat: 'CSV',
  selectors: ['lon','lat','label']
});

/**
 * TIPS KUALITAS:
 *  - Beri JARAK: kalau titik terasa terlalu rapat, kurangi N_POS atau
 *    pecah footprint jadi beberapa poligon kecil yg tersebar.
 *  - ANTI-DOMINASI: kalau 1 tambang sangat luas, jangan masukkan seluruhnya
 *    sebagai 1 poligon raksasa; ambil beberapa sub-area representatif.
 *  - HINDARI kolam & bangunan: jangan gambar poligon menutupi kolam
 *    pengendapan / fasilitas — fokus ke permukaan laterit terbuka.
 *  - SEIMBANG: usahakan footprint kecil di utara/selatan juga diwakili,
 *    bukan cuma Tambea, supaya model tidak bias spasial.
 */
