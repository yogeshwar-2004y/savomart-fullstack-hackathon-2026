"""Create a small Chennai GeoJSON extract from the Department of Posts OGD dataset."""

import argparse
import json
from pathlib import Path

from shapely.geometry import box, shape

from app.m1_areas.geometry import CHENNAI_BOUNDS


def iter_features(path: Path):
    text = path.read_text(encoding="utf-8")
    try:
        document = json.loads(text)
        yield from document.get("features", [document])
    except json.JSONDecodeError:
        for line in text.splitlines():
            if line.strip():
                yield json.loads(line)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    chennai = box(*CHENNAI_BOUNDS)
    features = [feature for feature in iter_features(args.source) if shape(feature["geometry"]).intersects(chennai)]
    args.destination.parent.mkdir(parents=True, exist_ok=True)
    args.destination.write_text(json.dumps({
        "type": "FeatureCollection",
        "name": "Chennai extract of All India Pincode Boundary Geo JSON",
        "source": "https://www.data.gov.in/catalog/all-india-pincode-boundary-geo-json",
        "license": "Government Open Data License - India",
        "features": features,
    }, separators=(",", ":")), encoding="utf-8")
    print(f"Wrote {len(features)} Chennai-intersecting features to {args.destination}")


if __name__ == "__main__":
    main()
