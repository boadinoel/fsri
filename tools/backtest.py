#!/usr/bin/env python3
"""
Minimal backtesting harness (no extra deps):
- Calls local FSRI API for a few test inputs
- Prints summary of scores and drivers
Usage:
  python tools/backtest.py http://127.0.0.1:8000
Default host: http://127.0.0.1:8000
"""
import json
import sys
import time
from urllib import request, parse

HOST = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000"

TESTS = [
    {"crop": "corn", "region": "US", "state": "IA", "export_flag": "false"},
    {"crop": "srw_wheat", "region": "US", "state": "IL", "export_flag": "false"},
    {"crop": "corn", "region": "US", "state": "IL", "export_flag": "false", "county_fips": "17031"},
]

def call_fsri(params: dict):
    qs = parse.urlencode(params)
    url = f"{HOST}/fsri?{qs}"
    with request.urlopen(url, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def main():
    results = []
    for p in TESTS:
        try:
            res = call_fsri(p)
            results.append(res)
            print("-", p["crop"], p.get("state"), "=>", res.get("fsri", {}).get("score"))
            time.sleep(0.2)
        except Exception as e:
            print("Error:", e)

    # Basic summary
    if not results:
        print("No results")
        return

    scores = [r.get("fsri", {}).get("score", 0.0) for r in results]
    avg = sum(scores) / len(scores)
    print("\nSummary")
    print("Samples:", len(scores))
    print("Avg FSRI:", round(avg, 1))
    for r in results:
        fsri = r.get("fsri", {})
        print("--", fsri.get("score"), fsri.get("drivers"))

if __name__ == "__main__":
    main()
