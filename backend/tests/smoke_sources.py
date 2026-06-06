"""Test all 6 data sources end-to-end and print a summary."""
import asyncio
import sys
import os

# cd to the backend dir from this script
HERE = os.path.dirname(os.path.abspath(__file__))
BACKEND = os.path.dirname(HERE)
os.chdir(BACKEND)
sys.path.insert(0, BACKEND)
sys.stdout.reconfigure(encoding="utf-8")

from app.core.state import state
from app.sources.earthquakes import EarthquakesSource
from app.sources.lightning import LightningSource
from app.sources.satellites import SatellitesSource
from app.sources.solar import SolarSource
from app.sources.volcanoes import VolcanoesSource
from app.sources.wildfires import WildfiresSource


async def test_one(name: str, src) -> bool:
    print(f"\n=== {name} ===")
    try:
        await src.update()
        s = state.status[name]
        print(f"  OK: items={s['items']} ok={s['ok']}")
        return True
    except Exception as e:
        print(f"  FAIL: {type(e).__name__}: {e}")
        return False
    finally:
        try:
            await src.close()
        except Exception:
            pass


async def main():
    print("Testing all 6 data sources against live APIs...")
    results = {}
    for name, cls in [
        ("satellites", SatellitesSource),
        ("lightning", LightningSource),
        ("earthquakes", EarthquakesSource),
        ("wildfires", WildfiresSource),
        ("volcanoes", VolcanoesSource),
        ("solar", SolarSource),
    ]:
        # Each source gets a fresh state
        state.satellites = {}
        state.lightning.clear()
        state.earthquakes = []
        state.wildfires = []
        state.volcanoes = []
        state.solar = None
        results[name] = await test_one(name, cls(state))

    print("\n\n=== SUMMARY ===")
    for n, ok in results.items():
        print(f"  {n}: {'OK' if ok else 'FAIL'}")


if __name__ == "__main__":
    asyncio.run(main())
