import os
import json
from argparse import ArgumentParser

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss


def expected_calibration_error(probs: np.ndarray, y: np.ndarray, bins: int = 10) -> float:
    edges = np.linspace(0, 1, bins + 1)
    ece = 0.0
    n = len(y)
    for i in range(bins):
        lo, hi = edges[i], edges[i + 1]
        mask = (probs >= lo) & (probs < hi) if i < bins - 1 else (probs >= lo) & (probs <= hi)
        if mask.sum() == 0:
            continue
        bin_conf = probs[mask].mean()
        bin_acc = y[mask].mean()
        ece += (mask.sum() / n) * abs(bin_acc - bin_conf)
    return float(ece)


def train_and_save(labels_csv: str = "data/mr_labels.csv", out_json: str = "data/movement_calibration.json") -> dict:
    df = pd.read_csv(labels_csv, parse_dates=["date"])  # columns: date, mr, y
    df = df.dropna(subset=["mr", "y"]).copy()
    if df.empty:
        raise RuntimeError("no data in labels CSV")

    X = df[["mr"]].values  # shape (n,1)
    y = df["y"].astype(int).values

    # If labels are single-class, fallback to default calibration
    unique = np.unique(y)
    if unique.size < 2:
        a = 0.08
        b = 0.0
        # Use heuristic probs from default mapping for metrics
        probs = 1.0 / (1.0 + np.exp(-(a * (X[:, 0] - 50.0) + b)))
        brier = brier_score_loss(y, probs)
        ece = expected_calibration_error(probs, y, bins=10)
        metrics = {"brier": float(brier), "ece_10": float(ece), "n": int(len(y)), "note": "single-class labels; default a,b used"}
        payload = {"a": a, "b": b, "metrics": metrics}
        os.makedirs(os.path.dirname(out_json), exist_ok=True)
        with open(out_json, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
        print(json.dumps(payload, indent=2))
        return payload

    # Fit logistic regression on MR (no scaling for simplicity)
    clf = LogisticRegression(max_iter=1000, class_weight="balanced")
    clf.fit(X, y)
    probs = clf.predict_proba(X)[:, 1]

    # Metrics
    brier = brier_score_loss(y, probs)
    ece = expected_calibration_error(probs, y, bins=10)

    # Convert coef/intercept to our a,b form: a*(mr-50)+b
    coef = float(clf.coef_[0][0])
    intercept = float(clf.intercept_[0])
    a = coef
    b = intercept - coef * 50.0

    metrics = {"brier": float(brier), "ece_10": float(ece), "n": int(len(y))}
    payload = {"a": a, "b": b, "metrics": metrics}

    os.makedirs(os.path.dirname(out_json), exist_ok=True)
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

    print(json.dumps(payload, indent=2))
    return payload


def main():
    p = ArgumentParser(description="Train logistic calibration for movement event from MR")
    p.add_argument("--labels", type=str, default="data/mr_labels.csv")
    p.add_argument("--out", type=str, default="data/movement_calibration.json")
    args = p.parse_args()
    train_and_save(args.labels, args.out)


if __name__ == "__main__":
    main()
