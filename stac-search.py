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
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urljoin

import requests

__version__ = "0.2.0"

USER_AGENT = f"stac-search/{__version__} (+https://clawhub.ai/skills/stac-search)"

# Local place-resolver (batch3 v0.2.0+)
try:
    from place_resolver import (
        resolve_place,
        get_preset,
        list_presets,
        format_bbox,
        PlaceNotFoundError,
        PRESETS as PLACE_PRESETS,
    )
except ImportError as _exc:
    print(
        f"Warning: place_resolver.py not found ({_exc}). --place/--preset disabled.",
        file=sys.stderr,
    )
    PLACE_PRESETS = {}

    def resolve_place(*args, **kwargs):
        raise RuntimeError("place_resolver.py missing")

    def get_preset(name):
        raise ValueError(f"Unknown preset: {name}")

    def list_presets():
        return "(place_resolver.py missing)"

    def format_bbox(b):
        return f"{b[0]} {b[1]} {b[2]} {b[3]}"

    class PlaceNotFoundError(ValueError):
        pass

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

# Task-oriented preset → STAC search (merged with place_resolver.PRESETS)
PRESETS = {
    **{k: v for k, v in PLACE_PRESETS.items()},  # all place_resolver presets
    "s2-l2a-china-low-cloud": {
        "endpoint": "planetary-computer",
        "collection": "sentinel-2-l2a",
        "bbox": (73.0, 18.0, 135.0, 54.0),
        "max_cloud_cover": 20.0,
        "description": "中国区域 Sentinel-2 L2A 低云量影像（云量≤20%）",
    },
    "landsat-china-low-cloud": {
        "endpoint": "planetary-computer",
        "collection": "landsat-c2-l2",
        "bbox": (73.0, 18.0, 135.0, 54.0),
        "max_cloud_cover": 20.0,
        "description": "中国 Landsat Collection 2 L2 低云量影像",
    },
    "cop-dem-30m-global": {
        "endpoint": "aws-earth-search",
        "collection": "cop-dem-glo-30",
        "bbox": (-180.0, -90.0, 180.0, 90.0),
        "description": "全球 Copernicus DEM 30m",
    },
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


def search_stac_for_aoi(
    aoi_manifest: Optional[Dict[str, Any]] = None,
    *,
    bbox: Optional[Tuple[float, ...]] = None,
    endpoint: str = "https://planetarycomputer.microsoft.com/api/stac/v1",
    collections: Optional[List[str]] = None,
    datetime_range: Optional[str] = None,
    limit: int = 10,
    max_cloud_cover: Optional[float] = None,
) -> Dict[str, Any]:
    """Phase 1+ 2026-07-26: 高级 API — 接受 AOI manifest 或 bbox，简化 STAC 搜索。

    是其他 skill（landsat-download / sentinel1-download / sentinel-downloader /
    modis-lst-download / change-detection 等）调用 STAC 的统一入口。

    Args:
        aoi_manifest: geoskill_core.manifest.AOIManifest.to_dict() 输出（含 bbox_wgs84）
        bbox: 显式 bbox tuple (W, S, E, N)
        endpoint: STAC endpoint URL
        collections: collection id 列表
        datetime_range: ISO8601 区间，如 "2024-01-01/2024-12-31"
        limit: 最大返回 item 数
        max_cloud_cover: 最大云量 (0-100)

    Returns:
        STAC search response (GeoJSON FeatureCollection)
    """
    if aoi_manifest and "bbox_wgs84" in aoi_manifest and bbox is None:
        bbox = tuple(aoi_manifest["bbox_wgs84"])
    if bbox is None:
        raise ValueError("must provide aoi_manifest (with bbox_wgs84) or bbox")
    if len(bbox) != 4:
        raise ValueError(f"bbox must be (W, S, E, N), got {bbox}")
    return search_stac(
        endpoint=endpoint,
        collections=collections,
        bbox=bbox,
        datetime_range=datetime_range,
        limit=limit,
        max_cloud_cover=max_cloud_cover,
    )


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


def format_results_geojson(data: Dict[str, Any]) -> str:
    """Return a GeoJSON FeatureCollection derived from a STAC search response.

    Each STAC Item becomes a Feature; the geometry is taken from the
    item's ``geometry`` field when present, otherwise the ``bbox`` is
    converted to a Polygon. ``properties`` carries the item id, collection,
    datetime, cloud cover and asset list.
    """
    features = data.get("features", [])
    out_features: List[Dict[str, Any]] = []
    for feat in features:
        props_in = feat.get("properties", {}) or {}
        bbox = feat.get("bbox")
        geom = feat.get("geometry")
        if not geom and bbox and len(bbox) == 4:
            minx, miny, maxx, maxy = bbox
            geom = {
                "type": "Polygon",
                "coordinates": [[
                    [minx, miny], [maxx, miny], [maxx, maxy],
                    [minx, maxy], [minx, miny],
                ]],
            }
        assets = feat.get("assets", {}) or {}
        asset_names = ",".join(sorted(assets.keys()))
        out_props: Dict[str, Any] = {
            "id": feat.get("id"),
            "collection": feat.get("collection") or props_in.get("collection"),
            "datetime": props_in.get("datetime"),
            "eo:cloud_cover": props_in.get("eo:cloud_cover"),
            "platform": props_in.get("platform"),
            "instruments": props_in.get("instruments"),
            "assets": asset_names,
            "stac_version": feat.get("stac_version"),
        }
        # Drop None values for a cleaner file
        out_props = {k: v for k, v in out_props.items() if v is not None}
        out_features.append({
            "type": "Feature",
            "geometry": geom,
            "properties": out_props,
        })
    fc: Dict[str, Any] = {
        "type": "FeatureCollection",
        "features": out_features,
    }
    return json.dumps(fc, ensure_ascii=False, indent=2)


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


def _write_qa_summary(parsed, resolved: Dict[str, Any], data: Dict[str, Any],
                      action: str) -> None:
    """Write a JSON run-summary sidecar (Phase 5 optimization).

    Records the resolved endpoint / collection / bbox / datetime filters,
    the action (search / list_collections / collection_info), and either
    the returned feature ids (search) or the count (list_collections /
    collection_info).
    """
    from datetime import datetime as _dt, timezone as _tz
    summary: Dict[str, Any] = {
        "skill": "stac-search",
        "command": action,
        "version": __version__,
        "timestamp": _dt.now(_tz.utc).isoformat(),
        "endpoint": resolved.get("endpoint"),
        "preset": parsed.preset,
        "collection": resolved.get("collection"),
        "bbox": list(resolved.get("bbox")) if resolved.get("bbox") else None,
        "place": parsed.place,
        "datetime": parsed.datetime,
        "max_cloud_cover": resolved.get("max_cloud_cover"),
        "limit": parsed.limit,
    }
    if action == "search":
        features = data.get("features", []) if isinstance(data, dict) else []
        summary["n_features"] = len(features)
        summary["feature_ids"] = [f.get("id") for f in features if isinstance(f, dict)]
    elif action == "list_collections":
        cols = data.get("collections", []) if isinstance(data, dict) else []
        summary["n_collections"] = len(cols)
        summary["collection_ids"] = [c.get("id") for c in cols
                                    if isinstance(c, dict)]
    elif action == "collection_info":
        info = data.get("info", {}) if isinstance(data, dict) else {}
        summary["info_id"] = info.get("id")
        summary["info_title"] = info.get("title")

    qa_p = Path(parsed.qa)
    qa_p.parent.mkdir(parents=True, exist_ok=True)
    qa_p.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def parse_args(args: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="STAC Universal Search Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples (batch3 v0.2.0+ — natural language place names + presets):

  # Preset: low-cloud Sentinel-2 over China
  python stac-search.py --preset s2-l2a-china-low-cloud \\
    --datetime 2024-06-01/2024-06-30 --limit 5

  # --place: just say "北京市"
  python stac-search.py --endpoint planetary-computer --collection sentinel-2-l2a \\
    --place "北京市" --datetime 2024-06-01/2024-06-30 --limit 5

  # --bbox still works (highest priority)
  python stac-search.py --preset planetary-computer --collection sentinel-2-l2a \\
    --bbox 120 30 121 31

  # List presets
  python stac-search.py --list-presets

  python stac-search.py --list-collections --preset aws-earth-search
  python stac-search.py --collection-info sentinel-2-l2a --preset planetary-computer
""",
    )
    # The source flag is now optional: a task-oriented --preset (in PRESETS) is also a "source"
    parser.add_argument("--preset", choices=list(PRESET_ENDPOINTS.keys()) + list(PRESETS.keys()),
                        help="Use a preset STAC endpoint OR a task-oriented preset (batch3+).")
    parser.add_argument("--endpoint", help="Custom STAC endpoint URL")
    parser.add_argument("--list-collections", action="store_true", help="List available collections")
    parser.add_argument("--list-presets", action="store_true", help="List task-oriented --preset names")
    parser.add_argument("--collection-info", metavar="COLLECTION", help="Get info for a specific collection")
    parser.add_argument("--collection", nargs="+", help="Collection ID(s) to search")
    parser.add_argument("--bbox", nargs=4, type=float, metavar=("MINX", "MINY", "MAXX", "MAXY"),
                        help="Bounding box (W S E N). Conflicts with --place.")
    parser.add_argument("--place", help="Place name (e.g. '北京市', '长江流域'). Offline + Nominatim.")
    parser.add_argument("--datetime", help="Datetime range (e.g., 2024-01-01/2024-12-31)")
    parser.add_argument("--max-cloud-cover", type=float, help="Maximum cloud cover percentage")
    parser.add_argument("--limit", type=int, default=10, help="Max results (default: 10)")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--format", choices=["json", "geojson", "table"], default=None,
                        help="Output format for the search results. Overrides --json when set. "
                             "'json' = raw STAC JSON; 'geojson' = a FeatureCollection derived "
                             "from the features; 'table' = a human-readable table (default).")
    parser.add_argument("--verbose", action="store_true", help="Show asset details")
    parser.add_argument("--list-assets", action="store_true", help="List assets for first result")
    parser.add_argument("--output", metavar="FILE", help="Write JSON output to FILE (in addition to stdout).")
    parser.add_argument("--qa", metavar="PATH", default=None,
                        help="Write a JSON run-summary sidecar to PATH (e.g. --qa run.qa.json). "
                             "Records the resolved endpoint / collection / bbox / datetime / "
                             "search filters, returned feature ids, and asset count so each "
                             "STAC query is auditable.")
    return parser.parse_args(args)


def resolve_args(parsed) -> Tuple[Dict, Dict]:
    """Apply --preset (task-oriented) and --place to derive endpoint/collection/bbox.

    Returns (resolved_args, diagnostics) dicts.
    """
    diag = {"actions": []}
    out = {
        "endpoint": None,
        "collection": parsed.collection,
        "bbox": tuple(parsed.bbox) if parsed.bbox else None,
        "max_cloud_cover": parsed.max_cloud_cover,
    }

    # Apply task-oriented preset (only if --preset is in PRESETS, not in PRESET_ENDPOINTS)
    if parsed.preset and parsed.preset in PRESETS:
        p = PRESETS[parsed.preset]
        diag["actions"].append(f"--preset '{parsed.preset}'")
        if "endpoint" in p:
            out["endpoint"] = PRESET_ENDPOINTS[p["endpoint"]]
            diag["actions"].append(f"  endpoint ← {p['endpoint']}")
        if "collection" in p and not out["collection"]:
            out["collection"] = [p["collection"]]
            diag["actions"].append(f"  collection ← {p['collection']}")
        if "bbox" in p and out["bbox"] is None:
            out["bbox"] = p["bbox"]
            diag["actions"].append(f"  bbox ← {format_bbox(p['bbox'])}")
        if "max_cloud_cover" in p and out["max_cloud_cover"] is None:
            out["max_cloud_cover"] = p["max_cloud_cover"]
            diag["actions"].append(f"  max_cloud_cover ← {p['max_cloud_cover']}")

    # --place → bbox (highest spatial priority after --bbox)
    if parsed.place and out["bbox"] is None:
        try:
            out["bbox"] = resolve_place(parsed.place)
            diag["actions"].append(f"  bbox ← --place '{parsed.place}' → {format_bbox(out['bbox'])}")
        except PlaceNotFoundError as exc:
            print(f"Error: {exc}", file=sys.stderr)
            sys.exit(2)

    # Resolve endpoint from PRESET_ENDPOINTS (only if user said --preset <endpoint-name>)
    if not out["endpoint"]:
        if parsed.preset and parsed.preset in PRESET_ENDPOINTS:
            out["endpoint"] = PRESET_ENDPOINTS[parsed.preset]
        elif parsed.endpoint:
            out["endpoint"] = get_endpoint(parsed.endpoint)
        else:
            out["endpoint"] = PRESET_ENDPOINTS["planetary-computer"]
            diag["actions"].append("  endpoint ← default: planetary-computer")

    return out, diag


def run(args: Optional[List[str]] = None) -> Tuple[str, int]:
    parsed = parse_args(args)

    if parsed.list_presets:
        return list_presets(), 0

    try:
        if parsed.list_collections:
            resolved, _ = resolve_args(parsed)
            endpoint = resolved["endpoint"]
            collections = list_collections(endpoint)
            output = json.dumps(collections, indent=2) if parsed.json else "\n".join(
                f"  {c['id']}: {c.get('title', 'N/A')}" for c in collections
            )
            if parsed.output:
                Path(parsed.output).write_text(output, encoding="utf-8")
            if parsed.qa:
                try:
                    _write_qa_summary(parsed, resolved,
                                      {"type": "CollectionList",
                                       "collections": collections},
                                      "list_collections")
                except OSError as e:
                    print(f"WARN: --qa sidecar could not be written: {e}",
                          file=sys.stderr)
            return output, 0

        if parsed.collection_info:
            resolved, _ = resolve_args(parsed)
            info = get_collection_info(resolved["endpoint"], parsed.collection_info)
            output = json.dumps(info, indent=2) if parsed.json else (
                f"Collection: {info.get('id')}\n"
                f"Title: {info.get('title', 'N/A')}\n"
                f"Description: {info.get('description', 'N/A')[:200]}\n"
                f"License: {info.get('license', 'N/A')}\n"
                f"Extent: {json.dumps(info.get('extent', {}), indent=2)}"
            )
            if parsed.output:
                Path(parsed.output).write_text(output, encoding="utf-8")
            if parsed.qa:
                try:
                    _write_qa_summary(parsed, resolved,
                                      {"type": "CollectionInfo", "info": info},
                                      "collection_info")
                except OSError as e:
                    print(f"WARN: --qa sidecar could not be written: {e}",
                          file=sys.stderr)
            return output, 0

        resolved, diag = resolve_args(parsed)
        # Print diagnostics on stderr (so stdout stays pure JSON if --json)
        for line in diag["actions"]:
            print(line, file=sys.stderr)
        data = search_stac(
            endpoint=resolved["endpoint"],
            collections=resolved["collection"],
            bbox=resolved["bbox"],
            datetime_range=parsed.datetime,
            limit=parsed.limit,
            max_cloud_cover=resolved["max_cloud_cover"],
        )
        if parsed.format == "json" or (parsed.format is None and parsed.json):
            output = json.dumps(data, indent=2)
        elif parsed.format == "geojson":
            output = format_results_geojson(data)
        elif parsed.format == "table":
            output = format_results_table(data, verbose=parsed.verbose)
        elif parsed.list_assets:
            features = data.get("features", [])
            if not features:
                return "No results to list assets for.", 0
            output = format_assets_list(features[0])
        elif parsed.json:
            output = json.dumps(data, indent=2)
        else:
            output = format_results_table(data, verbose=parsed.verbose)
        if parsed.output:
            Path(parsed.output).write_text(output, encoding="utf-8")

        # Phase 5: --qa sidecar summary for the search action.
        if parsed.qa:
            try:
                _write_qa_summary(parsed, resolved, data, "search")
            except OSError as e:
                print(f"WARN: --qa sidecar could not be written: {e}", file=sys.stderr)
        return output, 0

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
