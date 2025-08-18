# Testing the Argentis FSRI-Lite Pro API

This document provides instructions for testing the FSRI API using curl commands or the provided test script.

## Prerequisites

1. Install required tools:
   - [curl](https://curl.se/)
   - [jq](https://stedolan.github.io/jq/) (for pretty-printing JSON)
   - Python 3.8+

2. Start the API server:
   ```bash
   uvicorn app:app --reload
   ```

## Manual Testing with curl

### 1. Health Check
```bash
curl "http://localhost:8000/status"
```

### 2. Get FSRI Score
```bash
# Basic request
curl "http://localhost:8000/fsri?crop=corn&state=IL"

# With export restrictions
curl "http://localhost:8000/fsri?crop=srw_wheat&state=IA&export_flag=true"

# With county FIPS for biosecurity
curl "http://localhost:8000/fsri?crop=corn&state=MN&county_fips=17043"
```

### 3. Log a Decision
```bash
curl -X POST "http://localhost:8000/log-decision" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -H "ARGENTIS_API_KEY: your_api_key_here" \
  -d "crop=corn&region=US&fsri=45.2&action=test&notes=Test+decision&drivers=[]"
```

### 4. Export Data
```bash
curl "http://localhost:8000/export?crop=corn&region=US&days=30"
```

## Automated Testing

### Using the Test Script
1. Make the script executable:
   ```bash
   chmod +x test_api.sh
   ```

2. Edit the script to set your API key:
   ```bash
   API_KEY="your_api_key_here"
   ```

3. Run the tests:
   ```bash
   ./test_api.sh
   ```

## Expected Output

### Health Check (`GET /status`)
```json
{
  "ok": true,
  "time": "2024-08-18T12:00:00Z"
}
```

### FSRI Response (`GET /fsri`)
```json
{
  "fsri": 45.2,
  "subScores": {
    "production": 38.5,
    "movement": 52.1,
    "policy": 0.0,
    "biosecurity": 35.8
  },
  "drivers": [
    "Elevated waterway transport risk",
    "Normal production conditions",
    "No recent HPAI outbreaks detected"
  ],
  "timestamp": "2024-08-18T12:00:00Z",
  "confidence": "Medium",
  "horizons": {
    "d5": 44.8,
    "d15": 43.2,
    "d30": 41.5
  },
  "movement_event_7d": {
    "p": 0.25,
    "reason": "Low-moderate risk with some disruption potential"
  }
}
```

### Log Decision Response (`POST /log-decision`)
```json
{
  "status": "logged",
  "timestamp": "2024-08-18T12:00:00Z"
}
```

## Troubleshooting

1. **Connection refused**: Make sure the API server is running
2. **404 Not Found**: Check the endpoint URL and parameters
3. **401 Unauthorized**: Verify the API key in the request header
4. **500 Internal Server Error**: Check the server logs for details
