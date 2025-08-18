import httpx
import pytest

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

def test_get_nass_data_http_error(mocker):
    """Test that a non-200 response is handled gracefully."""
    mock_response = mocker.Mock()
    mock_response.status_code = 400
    mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "Bad Request", request=mocker.Mock(), response=mock_response
    )
    mocker.patch("httpx.get", return_value=mock_response)

    value = get_nass_data(api_key="fake_key", year="2023")
    assert value is None

def test_get_nass_data_no_data(mocker):
    """Test that an empty data list is handled."""
    mock_response = mocker.Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"data": []}
    mocker.patch("httpx.get", return_value=mock_response)

    value = get_nass_data(api_key="fake_key", year="2023")
    assert value is None
