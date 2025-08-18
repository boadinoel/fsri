# FSRI-Lite: Test Harness Specification

**Executive Summary:** This document details the testing strategy for FSRI-Lite v1.0. A robust test harness is critical for ensuring code quality, preventing regressions, and enabling rapid development. Our strategy employs a standard testing pyramid: a wide base of fast unit tests, a smaller set of integration tests for key I/O points, and a handful of end-to-end tests to validate the full system. We will use the `pytest` framework for its simplicity and powerful features like fixtures and mocking.

---

### 1. Framework and Setup

*   **Framework**: `pytest`
*   **Mocking Library**: `pytest-mock` (a wrapper around `unittest.mock`)
*   **Test Location**: All tests will reside in the `/tests` directory.
*   **Dependencies**: Add `pytest` and `pytest-mock` to a new `requirements-dev.txt` file.

    ```text
    # requirements-dev.txt
    pytest
    pytest-mock
    ```

*   **Running Tests**: Tests will be executed from the root directory via the command:

    ```bash
    python -m pytest
    ```

### 2. Unit Tests

**Goal**: To test individual functions and classes in isolation. These tests should be fast and have no external dependencies (no network, no filesystem).

*   **Location**: `/tests/unit/`
*   **Structure**: Test files will mirror the application structure, e.g., `tests/unit/test_production.py` will test `services/production.py`.
*   **Key Areas to Test**:
    1.  **Scoring Logic**: For each service (`production`, `movement`, `policy`, `biosecurity`, `fuse`), create tests that provide known inputs and assert that the calculated score is correct. Test edge cases like zero values, max values, and error conditions.
    2.  **Driver Logic**: Test the functions that generate the human-readable driver strings. Ensure they trigger on the correct thresholds.
    3.  **Utility Functions**: Test helper functions like the confidence calculator in `services/utils.py`.

*   **Example Test Case (`tests/unit/test_policy.py`)**:

    ```python
    from services.policy import get_policy_risk

    def test_get_policy_risk_with_flag():
        """Test that policy risk is high when the export flag is true."""
        risk, drivers = get_policy_risk(export_flag=True)
        assert risk == 70.0
        assert len(drivers) == 1
        assert "Export restrictions in effect" in drivers[0]

    def test_get_policy_risk_without_flag():
        """Test that policy risk is zero when the export flag is false."""
        risk, drivers = get_policy_risk(export_flag=False)
        assert risk == 0.0
        assert len(drivers) == 0
    ```

### 3. Integration Tests

**Goal**: To test the interaction between our application and external systems, primarily the data source APIs.

*   **Location**: `/tests/integration/`
*   **Strategy**: We will use `pytest` fixtures and the `mocker` fixture from `pytest-mock` to replace live API calls with predefined responses. This allows us to test our client-side logic (request formatting, response parsing, error handling) without relying on a live network connection.

*   **Key Areas to Test**:
    1.  **NASS API Client**: Test that `get_nass_data` in `services/production.py` correctly handles a successful JSON response, a 400 error, and a 500 error.
    2.  **USGS API Client**: Test that `get_movement_risk` in `services/movement.py` can parse a valid USGS response and correctly handles cases where a gauge's data is missing.
    3.  **Supabase Client**: Test that the `log_decision` function in `app.py` correctly constructs and attempts to send the payload to Supabase.

*   **Example Test Case (`tests/integration/test_production_integration.py`)**:

    ```python
    import httpx
    from services.production import get_nass_data

    def test_get_nass_data_success(mocker):
        """Test that NASS data is correctly parsed on a 200 OK response."""
        # Mock the httpx.get call
        mock_response = mocker.Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": [{"Value": "75"}]
        }
        mocker.patch("httpx.get", return_value=mock_response)

        value = get_nass_data(api_key="fake_key", year="2023")
        assert value == 75.0
    ```

### 4. End-to-End (E2E) Tests

**Goal**: To simulate a real user interaction by making live HTTP requests to a running instance of our application.

*   **Location**: `/tests/e2e/`
*   **Strategy**: These tests will use a library like `httpx` to make calls to the main API endpoints (`/status`, `/fsri`) of a locally running server. They will assert that the HTTP status code is correct and that the JSON response body has the expected structure.

*   **Key Test Cases**:
    1.  `test_status_endpoint`: Call `/status` and assert a `200 OK` response.
    2.  `test_fsri_endpoint`: Call `/fsri` and assert a `200 OK` response with a valid FSRI JSON payload. This test will use mocking to prevent the live server from making outbound calls to real data sources during the test run.
