"""ML model loading & prediction with uncertainty."""
import os, joblib, numpy as np

FEATS = ["iron_oxide", "ferrous", "clay", "ndvi",
         "elevation", "slope", "curvature", "twi"]

ML_OUT = os.path.join(os.path.dirname(__file__), "..", "ml", "outputs")


def load_model():
    p = os.path.join(ML_OUT, "nickelscope_model_hostrock.joblib")
    return joblib.load(p) if os.path.exists(p) else None


def predict_grid(grid_df, model_dict):
    m = model_dict["model"]
    out = grid_df.copy()
    X = out[model_dict["features"]].values
    out["probability"] = m.predict_proba(X)[:, 1]
    preds = np.array([tree.predict_proba(X)[:, 1] for tree in m.estimators_])
    out["uncertainty"] = preds.std(axis=0)
    return out
