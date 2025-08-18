import os
import glob
import json
import sys
from argparse import ArgumentParser
from datetime import timedelta

import pandas as pd
import numpy as np

# Ensure project root is importable when running as a script
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from settings import USGS_GAUGES


def _compute_site_risk(gauge_ft: float, low: float, high: float) -> float:
    if np.isnan(gauge_ft):
        return 0.3  # default moderate
    if gauge_ft <= low:
        return 1.0
    if gauge_ft >= high:
        return 0.0
    return (high - gauge_ft) / (high - low)


def build_mr_and_labels(data_dir: str = "data", out_path: str = "data/mr_labels.csv") -> str:
    # Load per-site feature CSVs
    files = sorted(glob.glob(os.path.join(data_dir, "usgs_*.csv")))
    if not files:
        raise FileNotFoundError(f"no usgs_*.csv files in {data_dir}; run tools/fetch_history.py first")

    site_frames = []
    meta = {}
    for f in files:
        site_id = os.path.basename(f).split("_")[1]
        # map thresholds by site_id
        for gname, cfg in USGS_GAUGES.items():
            if cfg["site_id"] == site_id:
                meta[site_id] = (cfg["low_threshold"], cfg["high_threshold"])
                break
        df = pd.read_csv(f, parse_dates=["date"]).set_index("date")
        df = df[["gauge_ft"]].rename(columns={"gauge_ft": f"gauge_{site_id}"})
        site_frames.append(df)
    # Align on date
    all_df = pd.concat(site_frames, axis=1).sort_index()

    # Compute per-day MR and label (any-site 7d low-water)
    risks = []
    low_flags = []
    for site_id, (low, high) in meta.items():
        gcol = f"gauge_{site_id}"
        r = all_df[gcol].apply(lambda v, lo=low, hi=high: _compute_site_risk(v, lo, hi))
        risks.append(r)
        low_flags.append((all_df[gcol] <= low).astype(int))
    if not risks:
        raise RuntimeError("no matched sites against USGS_GAUGES")

    mr_series = 100.0 * pd.concat(risks, axis=1).mean(axis=1)
    low_any = pd.concat(low_flags, axis=1).max(axis=1)
    # forward 7-day event: if any low flag occurs in next 7 days
    y = low_any.rolling(window=7, min_periods=1).max().shift(-6)

    ds = pd.DataFrame({
        "mr": mr_series,
        "y": y,
    }).dropna()

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    ds.to_csv(out_path, index_label="date")
    return out_path


def main():
    p = ArgumentParser(description="Build MR time series and 7d labels from site features")
    p.add_argument("--data_dir", type=str, default="data")
    p.add_argument("--out", type=str, default="data/mr_labels.csv")
    args = p.parse_args()
    path = build_mr_and_labels(args.data_dir, args.out)
    print(f"wrote {path}")


if __name__ == "__main__":
    main()
