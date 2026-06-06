"""
NickelScope - Fase 3b: Host-Rock Constrained Prospectivity
- Hitung ulang dist_um dari GEOLOGI RESMI (GeoMap 1:100k Kolaka, WGS84)
- Saring label ke domain host-rock (ultramafik + buffer)
- Retrain JUJUR (spatial CV) + bandingkan vs model lama (terkontaminasi)
"""
import warnings; warnings.filterwarnings('ignore')
import geopandas as gpd, pandas as pd, numpy as np, joblib, os
from shapely.geometry import Point
from shapely.ops import unary_union
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import StratifiedGroupKFold, cross_val_predict
from sklearn.metrics import roc_auc_score, classification_report
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt

os.makedirs("ml/outputs", exist_ok=True)
F8 = ["iron_oxide","ferrous","clay","ndvi","elevation","slope","curvature","twi"]

# ---------- 1) Geologi resmi -> ultramafik ----------
g = gpd.read_file("kolaka/geologi_ar_100k_kolaka.shp")[["NAMOBJ","geometry"]]
um = unary_union(g[g.NAMOBJ=="Ultramafic Complex"].to_crs(32751).geometry.tolist())

_D = "data" if os.path.exists("data/nickelscope_features_v2.csv") else "."
df = pd.read_csv(f"{_D}/nickelscope_features_v2.csv")
pts = gpd.GeoDataFrame(df.copy(),
        geometry=[Point(xy) for xy in zip(df.lon, df.lat)], crs=4326).to_crs(32751)
df["dist_um"] = pts.distance(um).values   # dist_um BENAR (dari geologi resmi)

# ---------- 2) Domain host-rock pada beberapa buffer ----------
print("=== Komposisi domain host-rock (ultramafik + buffer) ===")
print(f"{'buffer(m)':>9} {'positif':>8} {'negatif':>8}")
for buf in [0,250,500,1000]:
    d = df[df.dist_um<=buf]
    print(f"{buf:>9} {(d.label==1).sum():>8} {(d.label==0).sum():>8}")

# ---------- 3) Dataset terkurasi (in-domain, buffer 500 m) ----------
BUF = 500
dom = df[df.dist_um<=BUF].copy()
print(f"\nDipakai buffer {BUF} m -> {len(dom)} titik "
      f"(positif={int((dom.label==1).sum())}, negatif={int((dom.label==0).sum())})")
print(f"Positif terbuang (false-positive sedimen): {int((df.label==1).sum()-(dom.label==1).sum())}")

# ---------- 4) Retrain spatial CV: lama (semua) vs jujur (in-domain) ----------
def spatial_auc(data, feats):
    y = data.label.values.astype(int)
    BLK=0.03
    gx=((data.lon-data.lon.min())//BLK).astype(int).astype(str)
    gy=((data.lat-data.lat.min())//BLK).astype(int).astype(str)
    grp=(gx+"_"+gy).values
    m=RandomForestClassifier(n_estimators=400,min_samples_leaf=2,
                             class_weight="balanced",random_state=42,n_jobs=-1)
    n_splits=min(5, pd.Series(grp).nunique())
    cv=StratifiedGroupKFold(n_splits,shuffle=True,random_state=42)
    p=cross_val_predict(m,data[feats].values,y,cv=cv,groups=grp,
                        method="predict_proba",n_jobs=-1)[:,1]
    return roc_auc_score(y,p), p, y

auc_old,_,_   = spatial_auc(df,  F8)
auc_dom,p,y   = spatial_auc(dom, F8)
print(f"\n=== Spatial CV AUC ===")
print(f"  Model LAMA (650 titik, terkontaminasi) : {auc_old:.3f}  <- menyesatkan")
print(f"  Model JUJUR (in-domain host-rock)      : {auc_dom:.3f}  <- valid geologis")
print("\nClassification report (model jujur):")
print(classification_report(y,(p>=0.5).astype(int),target_names=["non-prospek","prospek"]))

# ---------- 5) Fit final + importance + simpan ----------
final = RandomForestClassifier(n_estimators=400,min_samples_leaf=2,
            class_weight="balanced",random_state=42,n_jobs=-1).fit(dom[F8].values, dom.label.values.astype(int))
imp = pd.Series(final.feature_importances_, index=F8).sort_values()
print("\nFeature importance (model jujur):")
for f,v in imp[::-1].items(): print(f"  {f:<11} {v:.3f}")

dom.to_csv("ml/outputs/features_hostrock.csv", index=False)
joblib.dump({"model":final,"features":F8,"buffer_m":BUF}, "ml/outputs/nickelscope_model_hostrock.joblib")

imp.plot.barh(color="#0a3d62", title="Feature Importance (Host-Rock Model)")
plt.tight_layout(); plt.savefig("ml/outputs/hostrock_importance.png", dpi=130)
print("\nDisimpan: features_hostrock.csv, nickelscope_model_hostrock.joblib, hostrock_importance.png")
