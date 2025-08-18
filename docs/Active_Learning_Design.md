# FSRI-Lite v1.0: ML & Active Learning Design

**Executive Summary:** This document proposes a strategy to evolve FSRI-Lite from a heuristic-based system to a predictive one with a continuous learning loop. We will begin by replacing the current hard-coded Movement Risk event predictor with a trainable logistic regression model. This model will be fed by new features from historical USGS and weather data. We will use the existing `decisions_log` table as our primary source of labels and implement an uncertainty sampling strategy to request human feedback, creating a virtuous cycle of model improvement with minimal annotation cost.

---

### 1. Current ML Inventory

The v0.1 codebase contains stubs and simple transforms, but no true machine learning models.

*   **Movement Event 'Prediction' (`services/ml.py:5`)**: This is a fixed logistic transformation of the Movement Risk (MR) score, not a predictive model. It maps the 0-100 MR score to a 0-1 probability but has no learned parameters.
*   **Kalman Filter Horizons (`services/fuse.py:88`)**: This is a classical time-series smoother used for trend-following forecasts. It does not incorporate external features and cannot predict non-linear changes.
*   **Training Stub (`services/ml.py:34`)**: The `train_movement_model` function is a placeholder with a `LinearRegression` model that is never used.

### 2. Proposed ML Upgrades

Our initial focus will be on building a robust, trainable classifier for the 7-day movement event.

#### 2.1. Movement 7-Day Low-Water Classifier

*   **Objective**: Predict the probability of a significant low-water event (any key gauge crossing its `low_threshold`) occurring in the next 7 days.
*   **Model**: Start with `sklearn.linear_model.LogisticRegression` for its simplicity and interpretability. The goal is a well-calibrated probability, not just a binary classification.
*   **Features (Initial Set)**:
    1.  `current_mr_score`: The existing top-level movement score.
    2.  `gauge_height_ma_7d`: 7-day moving average of each key gauge's height.
    3.  `gauge_height_delta_3d`: 3-day change in each key gauge's height.
    4.  `precip_sum_7d`: 7-day forecast of total precipitation in the relevant basin from Open-Meteo.
    5.  `spi_30d`: 30-day Standardized Precipitation Index (requires historical weather data) to capture drought conditions.
    6.  `seasonality_sin`, `seasonality_cos`: Sine/cosine transform of the day of the year to capture seasonal patterns.
*   **Labels & Labeling Strategy**:
    *   **Primary Source (Proxy Labels)**: The `decisions_log` table (`supabase_schema.sql:24`). An `action` like `reroute_barge` or `delay_shipment` taken by a user is a strong signal that a risk event was perceived. We will treat these as positive labels (`y=1`).
    *   **Ground Truth (Automated Labels)**: We will implement a daily job to check if any USGS gauge actually crossed its `low_threshold`. This provides a source of objective ground truth to validate the model and the proxy labels.
*   **Evaluation Metrics**:
    1.  **Brier Score**: Primary metric for measuring the accuracy of our probability predictions.
    2.  **Expected Calibration Error (ECE)**: To ensure the model is not over- or under-confident. An ECE plot will be a key diagnostic.
    3.  **Precision/Recall @ 5-day Lead Time**: To measure the business value of the predictions. Can we identify events 5 days out with reasonable precision?

#### 2.2. Data Augmentation

To support the feature set above, we need to build two new data ingestion services:

1.  **USGS History Service**: A utility to fetch the last 90 days of daily-average gauge height data for all sites listed in `settings.py`. This will populate the moving average and delta features.
2.  **Open-Meteo History Service**: A utility to fetch historical weather data to calculate the SPI, a critical drought indicator.

### 3. Active Learning Loop Design

We will use an **uncertainty sampling** strategy to intelligently request human feedback.

1.  **Prediction**: For every FSRI calculation, the Movement classifier produces a probability `p`.
2.  **Sampling**: If a prediction falls into the region of maximum uncertainty (e.g., `0.4 < p < 0.6`), we flag it as a candidate for human review.
3.  **Feedback Trigger**: A Slack webhook or email is sent to an analyst: *"FSRI model is uncertain about waterway risk for Corn/US. Is a disruption likely in the next 7 days? [Yes/No/Unsure]"*
4.  **Label Collection**: The response is logged to a new `human_labels` table, providing a high-quality, targeted label for the model.
5.  **Retraining**: A weekly cron job will:
    *   Pull the latest proxy labels from `decisions_log`.
    *   Pull the latest explicit labels from `human_labels`.
    *   Pull the latest ground truth from the automated gauge-crossing check.
    *   Retrain the `LogisticRegression` model on this fresh dataset.
    *   Run an evaluation script and publish updated metrics (Brier, ECE) to a dashboard/log.
    *   If metrics are satisfactory, the new model artifact is saved and replaces the old one in production.

### 4. Schema Updates & Privacy

*   **New Table: `human_labels`**
    *   A simple table is needed to store feedback from the active learning loop.
    ```sql
    CREATE TABLE IF NOT EXISTS human_labels (
        id BIGSERIAL PRIMARY KEY,
        prediction_ts TIMESTAMP WITH TIME ZONE NOT NULL,
        crop VARCHAR(50) NOT NULL,
        region VARCHAR(10) NOT NULL,
        model_probability DECIMAL(5,4) NOT NULL,
        human_label SMALLINT NOT NULL, -- 1 for event, 0 for no event, -1 for unsure
        analyst_id VARCHAR(100),
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    );
    ```
*   **Privacy Notes**: All data used (`decisions_log`, `human_labels`) is internal to Argentis. No PII is involved. The features are derived from public data sources. The system is self-contained and poses minimal privacy risk.
