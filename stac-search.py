#!/usr/bin/env python3
"""STAC Universal Search Tool - Search any STAC endpoint for geospatial data.

Privacy disclosure
------------------
When this script runs, it sends:
* Search queries to public STAC endpoints (Planetary Computer, AWS, etc.).
  No API keys, no local files, no PII are sent.

What is NOT sent: any data from the local filesystem, any environment
variables, any login credentials.

Public domain notice
--------------------
This tool queries public STAC APIs. Data retrieved is subject to the
licenses of the respective data providers.

License
-------
MIT-0 — No Attribution.
"""

import argparse
import json
import sys
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urljoin

import requests

__version__ = "0.1.0"

USER_AGENT = f"stac-search/{__version__} (+https://clawhub.ai/skills/stac-search)"

PRESET_ENDPOINTS = {
    "planetary-computer": "https://planetarycomputer.microsoft.com/api/stac/v1",
    "aws-earth-search": "https://earth-search.aws.element84.com/v1",
    "element84": "https://earth-search.aws.element84.com/v1",
    "gee": "https://earthengine-stac.storage.googleapis.com/catalog",
}

DEFAULT_COLLECTIONS = {
    "planetary-computer": ["sentinel-2-l2a", "landsat-c2-l2", "modis-14A2-061"],
    "aws-earth-search": ["sentinel-2-l2a", "cop-dem-glo-30"],
    "element84": ["sentinel-2-l2a", "cop-dem-glo-30"],
    "gee": ["COPERNICUS/S2_SR_HARMONIZED", "LANDSAT/LC08/C02/T1_L2"],
}


def get_endpoint(name_or_url: str) -> str:
    if name_or_url in PRESET_ENDPOINTS:
        return PRESET_ENDPOINTS[name_or_url]
    return name_or_url


def search_stac(
    endpoint: str,
    collections: Optional[List[str]] = None,
    bbox: Optional[Tuple[float, ...]] = None,
    datetime_range: Optional[str] = None,
    query: Optional[Dict[str, Any]] = None,
    limit: int = 10,
    max_cloud_cover: Optional[float] = None,
) -> Dict[str, Any]:
    url = urljoin(endpoint.rstrip("/") + "/", "search")
    payload: Dict[str, Any] = {"limit": limit}
    if collections:
        payload["collections"] = collections
    if bbox:
        payload["bbox"] = list(bbox)
    if datetime_range:
        payload["datetime"] = datetime_range
    if query:
        payload["query"] = query
    elif max_cloud_cover is not None:
        payload["query"] = {
            "eo:cloud_cover": {"lte": max_cloud_cover}
        }
    headers = {"User-Agent": USER_AGENT}
    resp = requests.post(url, json=payload, timeout=60, headers=headers)
    resp.raise_for_status()
    return resp.json()


def list_collections(endpoint: str) -> List[Dict[str, Any]]:
    url = urljoin(endpoint.rstrip("/") + "/", "collections")
    headers = {"User-Agent": USER_AGENT}
    resp = requests.get(url, timeout=30, headers=headers)
    resp.raise_for_status()
    data = resp.json()
    return data.get("collections", [])


def get_collection_info(endpoint: str, collection_id: str) -> Dict[str, Any]:
    url = urljoin(endpoint.rstrip("/") + "/", f"collections/{collection_id}")
    headers = {"User-Agent": USER_AGENT}
    resp = requests.get(url, timeout=30, headers=headers)
    resp.raise_for_status()
    return resp.json()


def list_assets(item: Dict[str, Any]) -> Dict[str, Any]:
    return item.get("properties", {}).get("assets", item.get("assets", {}))


def format_results_table(data: Dict[str, Any], verbose: bool = False) -> str:
    features = data.get("features", [])
    if not features:
        return "No results found."
    lines = []
    lines.append(f"Found {len(features)} item(s):\n")
    for i, feat in enumerate(features, 1):
        props = feat.get("properties", {})
        item_id = feat.get("id", "unknown")
        dt = props.get("datetime", "N/A")
        cloud = props.get("eo:cloud_cover", "N/A")
        collection = props.get("collection", feat.get("collection", "N/A"))
        bbox = feat.get("bbox", [])
        bbox_str = ", ".join(f"{v:.4f}" for v in bbox[:4]) if bbox else "N/A"
        lines.append(f"[{i}] {item_id}")
        lines.append(f"    Collection: {collection}")
        lines.append(f"    DateTime:   {dt}")
        lines.append(f"    Cloud Cover: {cloud}%")
        lines.append(f"    BBox:       {bbox_str}")
        if verbose:
            assets = feat.get("assets", {})
            if assets:
                lines.append(f"    Assets ({len(assets)}):")
                for name, asset in assets.items():
                    href = asset.get("href", "N/A")
                    atype = asset.get("type", "N/A")
                    lines.append(f"      - {name}: {atype}")
                    lines.append(f"        {href}")
        lines.append("")
    return "\n".join(lines)


def format_assets_list(item: Dict[str, Any]) -> str:
    assets = item.get("assets", {})
    if not assets:
        return "No assets found."
    lines = [f"Assets for item '{item.get('id', 'unknown')}':\n"]
    for name, info in assets.items():
        lines.append(f"  {name}:")
        lines.append(f"    Type: {info.get('type', 'N/A')}")
        lines.append(f"    Href: {info.get('href', 'N/A')}")
        roles = info.get("roles", [])
        if roles:
            lines.append(f"    Roles: {', '.join(roles)}")
        lines.append("")
    return "\n".join(lines)


def parse_args(args: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="STAC Universal Search Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  stac-search.py --preset planetary-computer --collection sentinel-2-l2a --bbox 120 30 121 31
  stac-search.py --endpoint https://earth-search.aws.element84.com/v1 --collection sentinel-2-l2a --limit 5
  stac-search.py --list-collections --preset aws-earth-search
  stac-search.py --collection-info sentinel-2-l2a --preset planetary-computer
  stac-search.py --preset planetary-computer --collection landsat-c2-l2 --bbox -122.5 37.5 -122.0 38.0 --datetime 2024-01-01/2024-06-30 --max-cloud-cover 20 --limit 5 --json
""",
    )
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--preset", choices=list(PRESET_ENDPOINTS.keys()), help="Use a preset STAC endpoint")
    source.add_argument("--endpoint", help="Custom STAC endpoint URL")
    parser.add_argument("--list-collections", action="store_true", help="List available collections")
    parser.add_argument("--collection-info", metavar="COLLECTION", help="Get info for a specific collection")
    parser.add_argument("--collection", nargs="+", help="Collection ID(s) to search")
    parser.add_argument("--bbox", nargs=4, type=float, metavar=("MINX", "MINY", "MAXX", "MAXY"), help="Bounding box")
    parser.add_argument("--datetime", help="Datetime range (e.g., 2024-01-01/2024-12-31)")
    parser.add_argument("--max-cloud-cover", type=float, help="Maximum cloud cover percentage")
    parser.add_argument("--limit", type=int, default=10, help="Max results (default: 10)")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--verbose", action="store_true", help="Show asset details")
    parser.add_argument("--list-assets", action="store_true", help="List assets for first result")
    return parser.parse_args(args)


def run(args: Optional[List[str]] = None) -> Tuple[str, int]:
    parsed = parse_args(args)
    try:
        if parsed.list_collections:
            endpoint = PRESET_ENDPOINTS.get(parsed.preset, parsed.endpoint) or PRESET_ENDPOINTS["planetary-computer"]
            collections = list_collections(endpoint)
            output = json.dumps(collections, indent=2) if parsed.json else "\n".join(
                f"  {c['id']}: {c.get('title', 'N/A')}" for c in collections
            )
            return output, 0

        if parsed.collection_info:
            endpoint = PRESET_ENDPOINTS.get(parsed.preset, parsed.endpoint) or PRESET_ENDPOINTS["planetary-computer"]
            info = get_collection_info(endpoint, parsed.collection_info)
            output = json.dumps(info, indent=2) if parsed.json else (
                f"Collection: {info.get('id')}\n"
                f"Title: {info.get('title', 'N/A')}\n"
                f"Description: {info.get('description', 'N/A')[:200]}\n"
                f"License: {info.get('license', 'N/A')}\n"
                f"Extent: {json.dumps(info.get('extent', {}), indent=2)}"
            )
            return output, 0

        endpoint = get_endpoint(parsed.preset or parsed.endpoint)
        bbox = tuple(parsed.bbox) if parsed.bbox else None
        data = search_stac(
            endpoint=endpoint,
            collections=parsed.collection,
            bbox=bbox,
            datetime_range=parsed.datetime,
            limit=parsed.limit,
            max_cloud_cover=parsed.max_cloud_cover,
        )
        if parsed.json:
            return json.dumps(data, indent=2), 0
        if parsed.list_assets:
            features = data.get("features", [])
            if not features:
                return "No results to list assets for.", 0
            return format_assets_list(features[0]), 0
        return format_results_table(data, verbose=parsed.verbose), 0

    except requests.HTTPError as e:
        return f"HTTP Error: {e.response.status_code} - {e.response.text[:200]}", 1
    except requests.ConnectionError:
        return f"Connection Error: Could not connect to endpoint", 1
    except requests.Timeout:
        return "Timeout: Request timed out", 1
    except Exception as e:
        return f"Error: {type(e).__name__}: {e}", 1


def main():
    output, code = run()
    print(output)
    sys.exit(code)


if __name__ == "__main__":
    main()
