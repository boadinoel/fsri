#!/bin/bash

# Test API endpoints for Argentis FSRI-Lite Pro
# Make sure the API is running before executing these tests

API_BASE="http://localhost:8000"
API_KEY="your_api_key_here"  # Replace with your actual API key

# Test 1: Health Check
echo "Testing /status endpoint..."
curl -s "$API_BASE/status" | jq .
echo ""

# Test 2: Get FSRI score for corn in Illinois
echo "Testing /fsri endpoint for corn in IL..."
curl -s "$API_BASE/fsri?crop=corn&state=IL" | jq .
echo ""

# Test 3: Get FSRI score for wheat with export restrictions
echo "Testing /fsri endpoint for wheat with export restrictions..."
curl -s "$API_BASE/fsri?crop=srw_wheat&state=IA&export_flag=true" | jq .
echo ""

# Test 4: Log a decision (requires API key)
echo "Testing /log-decision endpoint..."
curl -s -X POST "$API_BASE/log-decision" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -H "ARGENTIS_API_KEY: $API_KEY" \
  -d "crop=corn&region=US&fsri=45.2&action=test&drivers=[]" | jq .
echo ""

# Test 5: Export data
echo "Testing /export endpoint..."
curl -s "$API_BASE/export?crop=corn&region=US&days=30" | jq .
echo ""

echo "API tests completed."
