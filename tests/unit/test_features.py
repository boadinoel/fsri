import pandas as pd
import numpy as np
from datetime import date, timedelta

from services.history import build_features


def test_build_features_spi30_and_mas():
    # 120 days synthetic data
    dates = [date(2024, 1, 1) + timedelta(days=i) for i in range(120)]
    df = pd.DataFrame({
        "gauge_ft": np.linspace(10, 6, 120),
        "precip_mm": np.random.RandomState(0).gamma(2.0, 1.0, 120),
        "temp_c": 20.0,
        "rh": 60.0,
    }, index=dates)

    feat = build_features(df)
    # Columns exist
    for col in ["ma_7", "ma_30", "delta_3", "delta_7", "spi_30", "woy_sin", "woy_cos"]:
        assert col in feat.columns
    # Rolling windows should yield some non-null values after warmup
    assert feat["ma_7"].notna().sum() > 50
    assert feat["spi_30"].notna().sum() > 0
