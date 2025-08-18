# FSRI-Lite: v1.0 30/60/90 Day Roadmap

**Executive Summary:** This document outlines a concrete, time-boxed plan to address the gaps identified in the `Gap_Map.md` and deliver FSRI-Lite v1.0. The roadmap is phased to tackle the most critical foundational issues first (testing, configuration), then move to implementing the core ML capabilities, and finally focus on operational hardening and the active learning feedback loop.

---

### Phase 1: Foundations (Days 1-30)

**Goal:** De-risk the project by establishing a stable foundation for development. By the end of this phase, the system will be testable, configurable, and ready for ML integration.

| Week | Key Results | Acceptance Tests |
| :--- | :--- | :--- |
| **Week 1** | **Test Harness & Unit Tests:** Create `/tests` directory. Implement unit tests for all four scoring services (`production`, `movement`, `policy`, `biosecurity`) and the `fuse` service. | `pytest` runs successfully and achieves >80% line coverage on the five specified service modules. |
| **Week 2** | **Configuration as Code:** Create `config.yaml`. Migrate all weights, thresholds, and magic numbers from `.py` files into the new config. Add `PyYAML` to `requirements.txt`. | The application runs correctly using the new config file. Changing a weight in `config.yaml` and restarting the server is reflected in the `/fsri` API output. |
| **Week 3** | **Historical Data Ingestion:** Create `services/history.py` with functions to pull the last 90 days of data from USGS and Open-Meteo for all configured sites/locations. | A script `tools/fetch_history.py` can be run to successfully download and save historical data to a local `/data` directory as CSV files. |
| **Week 4** | **Integration & Backtesting:** Create integration tests that mock API calls to data sources. Expand `tools/backtest.py` to run the FSRI model against a specific date using the downloaded historical data. | `pytest` integration tests pass. `python tools/backtest.py --date 2023-10-01` produces a valid FSRI score without hitting live APIs. |

### Phase 2: ML Implementation (Days 31-60)

**Goal:** Replace the core heuristic model with a trainable, data-driven classifier and begin the process of systematic improvement.

| Week | Key Results | Acceptance Tests |
| :--- | :--- | :--- |
| **Week 5-6** | **Feature Engineering & Model Training:** Create `services/features.py` to generate the feature set defined in `Active_Learning_Design.md` from historical data. Update `services/ml.py` to train a `LogisticRegression` model on these features. | A script `tools/train_model.py` runs without errors, loads historical data, generates features, trains a model, and saves a `movement_model.pkl` file. The script also outputs Brier Score and ECE metrics. |
| **Week 7** | **Integrate Production Model:** The `/fsri` endpoint is updated to call the trained `movement_model.pkl` to get the movement event probability instead of the old heuristic. The result is incorporated into the MR score. | The `/fsri` endpoint returns a `movement_risk_prob` field in its JSON response. The value changes based on input features. The system is stable. |
| **Week 8** | **Initial Labeling & Retraining Pipeline:** Create the `human_labels` table in Supabase. Implement the weekly retraining cron job (as a manual script initially) that pulls labels from `decisions_log` and `human_labels` to retrain and evaluate the model. | `tools/retrain.py` successfully queries Supabase, runs the training process, and logs updated performance metrics. |

### Phase 3: Operational Hardening & Active Learning (Days 61-90)

**Goal:** Make the system robust, observable, and begin closing the human-in-the-loop feedback cycle.

| Week | Key Results | Acceptance Tests |
| :--- | :--- | :--- |
| **Week 9** | **Structured Logging:** Integrate structured logging (e.g., `structlog`) throughout the application. All API requests and key service operations should produce machine-readable JSON logs. | Running the application and hitting endpoints produces structured logs to `stdout`. Key fields like `request_id`, `endpoint`, and `duration_ms` are present. |
| **Week 10** | **Active Learning Feedback Hook:** Implement the uncertainty sampling logic. When a prediction's probability is between 0.4 and 0.6, trigger a webhook (e.g., to a Slack channel) asking for feedback. | A prediction in the uncertainty window successfully triggers a POST request to a configured webhook URL with the expected payload. |
| **Week 11** | **Secure Secret Management:** Replace `.env` file usage in production with a secure secret management system (e.g., Doppler, GitHub Secrets). Update deployment scripts to inject secrets at runtime. | The production application starts successfully without a `.env` file present. Secrets are confirmed to be loaded correctly from the new provider. |
| **Week 12** | **v1.0 Release Candidate:** Review all documentation, tests, and code. Freeze the feature set. Deploy the full system to a staging environment for final UAT. | All roadmap items are complete. The system is deployed and stable. A final review of the deliverables is signed off by the project owner. |
