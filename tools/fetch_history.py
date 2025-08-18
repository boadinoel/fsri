import asyncio
import os
import sys
from argparse import ArgumentParser

# Ensure project root is importable when running as a script
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from services.history import fetch_history


def main():
    p = ArgumentParser(description="Fetch USGS/Open-Meteo history and compute features")
    p.add_argument("--days", type=int, default=180, help="Days of history (90-365)")
    p.add_argument("--state", type=str, default="IL", help="US state for weather coords")
    p.add_argument("--out_dir", type=str, default="data", help="Output directory")
    args = p.parse_args()

    async def run():
        paths = await fetch_history(days=args.days, state=args.state, out_dir=args.out_dir)
        for site, path in paths.items():
            print(f"saved {site}: {path}")

    asyncio.run(run())


if __name__ == "__main__":
    main()
