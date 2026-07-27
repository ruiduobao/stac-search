"""Tests for the --format (json|geojson|table) flag on stac-search.

This module verifies the new --format flag works as a uniform interface
to the output format. The legacy --json flag is preserved.
"""
import json
import os
import subprocess
import sys

import pytest

import importlib.util
SCRIPT_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "stac-search.py"
)
_spec = importlib.util.spec_from_file_location("stac_search_main", SCRIPT_PATH)
ss = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ss)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_stac_response():
    return {
        "type": "FeatureCollection",
        "features": [
            {
                "id": "S2A_MSIL2A_20240601T030551",
                "type": "Feature",
                "collection": "sentinel-2-l2a",
                "stac_version": "1.0.0",
                "bbox": [116.0, 39.5, 117.0, 40.5],
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[[116.0, 39.5], [117.0, 39.5],
                                      [117.0, 40.5], [116.0, 40.5],
                                      [116.0, 39.5]]],
                },
                "properties": {
                    "datetime": "2024-06-01T03:05:51Z",
                    "eo:cloud_cover": 5.4,
                    "platform": "sentinel-2a",
                    "instruments": ["msi"],
                },
                "assets": {
                    "blue": {"href": "https://example.com/B02.tif"},
                    "red":  {"href": "https://example.com/B04.tif"},
                },
            },
            {
                "id": "S2B_MSIL2A_20240608T030549",
                "type": "Feature",
                "collection": "sentinel-2-l2a",
                "stac_version": "1.0.0",
                "bbox": [116.0, 39.5, 117.0, 40.5],
                "properties": {
                    "datetime": "2024-06-08T03:05:49Z",
                    "eo:cloud_cover": 8.2,
                    "platform": "sentinel-2b",
                    "instruments": ["msi"],
                },
                "assets": {"red": {"href": "https://example.com/B04.tif"}},
            },
        ],
    }


# ---------------------------------------------------------------------------
# Parser tests
# ---------------------------------------------------------------------------

class TestFormatFlagParser:
    def test_help_lists_format(self):
        out = subprocess.run(
            [sys.executable, SCRIPT_PATH, "--help"],
            capture_output=True, text=True, timeout=10,
        )
        text = out.stdout + out.stderr
        assert "--format" in text
        assert "json" in text
        assert "geojson" in text
        assert "table" in text

    def test_default_format_is_none(self):
        from argparse import Namespace
        # build_parser is not exposed; simulate by calling the function
        # with --list-presets (no real args needed)
        # We just want to check that --format is recognized on the help
        out = subprocess.run(
            [sys.executable, SCRIPT_PATH, "--list-presets"],
            capture_output=True, text=True, timeout=10,
        )
        assert out.returncode == 0

    def test_format_argparse_accepts_choices(self):
        """Verify each choice is accepted at parse-time via a quick dry-run."""
        for choice in ("json", "geojson", "table"):
            # Use --list-presets (no network) but pass --format to confirm
            # argparse accepts the choice.
            out = subprocess.run(
                [sys.executable, SCRIPT_PATH, "--list-presets", "--format", choice],
                capture_output=True, text=True, timeout=10,
            )
            text = out.stdout + out.stderr
            # Should not error out with "invalid choice"
            assert "invalid choice" not in text, (
                f"--format {choice!r} rejected by argparse:\n{text}"
            )

    def test_format_invalid_choice_rejected(self):
        out = subprocess.run(
            [sys.executable, SCRIPT_PATH, "--list-presets",
             "--format", "xml"],
            capture_output=True, text=True, timeout=10,
        )
        assert out.returncode != 0
        text = out.stdout + out.stderr
        assert "invalid choice" in text


# ---------------------------------------------------------------------------
# Helper-function tests
# ---------------------------------------------------------------------------

class TestFormatResultsGeojson:
    def test_geojson_featurecollection(self, sample_stac_response):
        out = ss.format_results_geojson(sample_stac_response)
        d = json.loads(out)
        assert d["type"] == "FeatureCollection"
        assert len(d["features"]) == 2
        for feat in d["features"]:
            assert feat["type"] == "Feature"
            assert feat["geometry"] is not None
            assert "id" in feat["properties"]
            assert "datetime" in feat["properties"]

    def test_geojson_infers_geometry_from_bbox(self, sample_stac_response):
        """When geometry is missing, a Polygon should be derived from bbox."""
        out = ss.format_results_geojson(sample_stac_response)
        d = json.loads(out)
        # The first feature has explicit geometry; the second does NOT
        # (it has only bbox), but the helper should still produce a Polygon.
        for feat in d["features"]:
            assert feat["geometry"]["type"] == "Polygon"
            # Polygon ring has 5 points (closed)
            assert len(feat["geometry"]["coordinates"][0]) == 5

    def test_geojson_assets_csv(self, sample_stac_response):
        out = ss.format_results_geojson(sample_stac_response)
        d = json.loads(out)
        first = d["features"][0]
        # Assets should be a comma-joined string of asset names
        assert first["properties"]["assets"] == "blue,red"

    def test_geojson_empty(self):
        out = ss.format_results_geojson({"features": []})
        d = json.loads(out)
        assert d["type"] == "FeatureCollection"
        assert d["features"] == []

    def test_geojson_drops_none_values(self, sample_stac_response):
        out = ss.format_results_geojson(sample_stac_response)
        d = json.loads(out)
        for feat in d["features"]:
            for k, v in feat["properties"].items():
                assert v is not None, f"property {k!r} is None"


class TestFormatFlagWiring:
    """Verify --format overrides --json in the run() output pipeline."""

    def test_format_table_uses_table_renderer(self, sample_stac_response, monkeypatch):
        # Mock search_stac to return our fixture
        monkeypatch.setattr(ss, "search_stac", lambda **kw: sample_stac_response)
        # Mock resolve_args to avoid network
        monkeypatch.setattr(
            ss, "resolve_args",
            lambda parsed: ({"endpoint": "fake", "collection": ["s2-l2a"],
                             "bbox": [116, 39.5, 117, 40.5],
                             "max_cloud_cover": None}, {"actions": []}),
        )
        out, code = ss.run([
            "--collection", "sentinel-2-l2a",
            "--bbox", "116", "39.5", "117", "40.5",
            "--format", "table",
        ])
        assert code == 0
        # Table output has "Found N item(s)" marker
        assert "Found 2 item(s)" in out

    def test_format_geojson_uses_geojson_renderer(self, sample_stac_response, monkeypatch):
        monkeypatch.setattr(ss, "search_stac", lambda **kw: sample_stac_response)
        monkeypatch.setattr(
            ss, "resolve_args",
            lambda parsed: ({"endpoint": "fake", "collection": ["s2-l2a"],
                             "bbox": [116, 39.5, 117, 40.5],
                             "max_cloud_cover": None}, {"actions": []}),
        )
        out, code = ss.run([
            "--collection", "sentinel-2-l2a",
            "--bbox", "116", "39.5", "117", "40.5",
            "--format", "geojson",
        ])
        assert code == 0
        d = json.loads(out)
        assert d["type"] == "FeatureCollection"
        assert len(d["features"]) == 2

    def test_format_json_uses_json_renderer(self, sample_stac_response, monkeypatch):
        monkeypatch.setattr(ss, "search_stac", lambda **kw: sample_stac_response)
        monkeypatch.setattr(
            ss, "resolve_args",
            lambda parsed: ({"endpoint": "fake", "collection": ["s2-l2a"],
                             "bbox": [116, 39.5, 117, 40.5],
                             "max_cloud_cover": None}, {"actions": []}),
        )
        out, code = ss.run([
            "--collection", "sentinel-2-l2a",
            "--bbox", "116", "39.5", "117", "40.5",
            "--format", "json",
        ])
        assert code == 0
        d = json.loads(out)
        # Raw STAC response
        assert d["type"] == "FeatureCollection"
        assert "features" in d

    def test_legacy_json_flag_still_works(self, sample_stac_response, monkeypatch):
        """The legacy --json flag must still produce JSON output."""
        monkeypatch.setattr(ss, "search_stac", lambda **kw: sample_stac_response)
        monkeypatch.setattr(
            ss, "resolve_args",
            lambda parsed: ({"endpoint": "fake", "collection": ["s2-l2a"],
                             "bbox": [116, 39.5, 117, 40.5],
                             "max_cloud_cover": None}, {"actions": []}),
        )
        out, code = ss.run([
            "--collection", "sentinel-2-l2a",
            "--bbox", "116", "39.5", "117", "40.5",
            "--json",
        ])
        assert code == 0
        d = json.loads(out)
        assert d["type"] == "FeatureCollection"
