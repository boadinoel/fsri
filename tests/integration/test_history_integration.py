import httpx
import pytest

from services.history import get_usgs_history

# Mark all tests in this file as async for pytest-asyncio
pytestmark = pytest.mark.asyncio


async def test_get_usgs_history_success(mocker):
    """Test successful retrieval of USGS history data."""
    mock_response_json = {"value": {"timeSeries": [{"sourceInfo": {}}]}}
    
    mock_response = mocker.AsyncMock()
    mock_response.status_code = 200
    mock_response.json.return_value = mock_response_json

    mock_client = mocker.AsyncMock()
    mock_client.get.return_value = mock_response
    
    mocker.patch("httpx.AsyncClient", return_value=mocker.MagicMock(__aenter__=mocker.AsyncMock(return_value=mock_client)))

    data = await get_usgs_history(site_id="07032000")
    assert data == mock_response_json


async def test_get_usgs_history_http_error(mocker):
    """Test that an HTTP error is handled gracefully."""
    mock_response = mocker.AsyncMock()
    mock_response.status_code = 500
    mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "Server Error", request=mocker.Mock(), response=mock_response
    )

    mock_client = mocker.AsyncMock()
    mock_client.get.return_value = mock_response

    mocker.patch("httpx.AsyncClient", return_value=mocker.MagicMock(__aenter__=mocker.AsyncMock(return_value=mock_client)))

    data = await get_usgs_history(site_id="07032000")
    assert data is None
