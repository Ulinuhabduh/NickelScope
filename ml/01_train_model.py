"""
NickelScope - Fase 3: Pemodelan ML (Prospectivity)
- Random Forest & XGBoost
- Spatial (block) cross-validation vs random CV  -> bukti rigor metodologi
- Feature importance + simpan model untuk peta prediksi (Fase 4)
"""
import os, numpy as np, pandas as pd, joblib
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import (StratifiedKFold, StratifiedGroupKFold,
                                     cross_val_predict)
from sklearn.metrics import (roc_auc_score, roc_curve, classification_report,
                             confusion_matrix)
import xgboost as xgb
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt

os.makedirs("ml/outputs", exist_ok=True)

# ---------- 1) Data ----------
_D = "data" if os.path.exists("data/nickelscope_features.csv") else "."
df = pd.read_csv(f"{_D}/nickelscope_features.csv")
FEATURES = ["iron_oxide","ferrous","clay","ndvi",
            "elevation","slope","curvature","twi"]
X = df[FEATURES].values
y = df["label"].values.astype(int)
print(f"Data: {len(df)} titik | positif={y.sum()} negatif={(y==0).sum()}")

# ---------- 2) Spatial blocks (untuk spatial CV) ----------
BLOCK = 0.03  # ~3 km
bx = ((df.lon - df.lon.min()) // BLOCK).astype(int).astype(str)
by = ((df.lat - df.lat.min()) // BLOCK).astype(int).astype(str)
groups = (bx + "_" + by).values
print(f"Jumlah blok spasial: {pd.Series(groups).nunique()}")

# ---------- 3) Model ----------
models = {
  "RandomForest": RandomForestClassifier(
      n_estimators=400, min_samples_leaf=2, class_weight="balanced",
      random_state=42, n_jobs=-1),
  "XGBoost": xgb.XGBClassifier(
      n_estimators=400, max_depth=4, learning_rate=0.05,
      subsample=0.8, colsample_bytree=0.8, eval_metric="logloss",
      random_state=42),
}

random_cv  = StratifiedKFold(5, shuffle=True, random_state=42)
spatial_cv = StratifiedGroupKFold(5, shuffle=True, random_state=42)

print("\n=== Cross-Validation AUC ===")
print(f"{'Model':<14}{'Random CV':>12}{'Spatial CV':>13}  (spatial = jujur)")
results = {}
for name, model in models.items():
    p_rand = cross_val_predict(model, X, y, cv=random_cv,
                               method="predict_proba", n_jobs=-1)[:,1]
    p_spat = cross_val_predict(model, X, y, cv=spatial_cv, groups=groups,
                               method="predict_proba", n_jobs=-1)[:,1]
    auc_r, auc_s = roc_auc_score(y, p_rand), roc_auc_score(y, p_spat)
    results[name] = dict(p_spat=p_spat, auc_r=auc_r, auc_s=auc_s)
    print(f"{name:<14}{auc_r:>12.3f}{auc_s:>13.3f}")

# ---------- 4) Pilih model terbaik (berdasar spatial AUC) ----------
best = max(results, key=lambda k: results[k]["auc_s"])
print(f"\nModel terbaik (spatial AUC): {best} = {results[best]['auc_s']:.3f}")

p_spat = results[best]["p_spat"]
y_pred = (p_spat >= 0.5).astype(int)
print("\n=== Classification report (spatial CV) ===")
print(classification_report(y, y_pred, target_names=["non-prospek","prospek"]))
print("Confusion matrix:\n", confusion_matrix(y, y_pred))

# ---------- 5) Fit final di semua data + feature importance ----------
final = models[best].fit(X, y)
if hasattr(final, "feature_importances_"):
    imp = pd.Series(final.feature_importances_, index=FEATURES).sort_values()
    print("\n=== Feature importance ===")
    for f, v in imp[::-1].items():
        print(f"  {f:<11} {v:.3f}")

# ---------- 6) Plot ROC + importance ----------
fig, ax = plt.subplots(1, 2, figsize=(12,4.5))
for name in results:
    fpr, tpr, _ = roc_curve(y, results[name]["p_spat"])
    ax[0].plot(fpr, tpr, label=f"{name} (AUC={results[name]['auc_s']:.3f})")
ax[0].plot([0,1],[0,1],"k--",lw=.8); ax[0].set_title("ROC (Spatial CV)")
ax[0].set_xlabel("FPR"); ax[0].set_ylabel("TPR"); ax[0].legend()
imp.plot.barh(ax=ax[1], color="#0a3d62")
ax[1].set_title(f"Feature Importance ({best})")
plt.tight_layout(); plt.savefig("ml/outputs/model_eval.png", dpi=130)
print("\nPlot disimpan: ml/outputs/model_eval.png")

# ---------- 7) Simpan model ----------
joblib.dump({"model": final, "features": FEATURES}, "ml/outputs/nickelscope_model.joblib")
print("Model disimpan: ml/outputs/nickelscope_model.joblib")
