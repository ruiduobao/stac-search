"""Phase 5: --qa sidecar summary tests for stac-search."""
import argparse
import json
import os
import sys
from unittest.mock import patch

import pytest

# Make the script importable
HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(HERE, ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import stac_search  # noqa: E402


def _mock_search_response():
    return {
        "type": "FeatureCollection",
        "features": [
            {"id": "S2A_20240101", "type": "Feature",
             "geometry": None, "properties": {}, "assets": {}},
            {"id": "S2A_20240115", "type": "Feature",
             "geometry": None, "properties": {}, "assets": {}},
        ],
    }


def _mock_list_collections_response():
    return {"collections": [{"id": "sentinel-2-l2a"}, {"id": "landsat-8-l1"}]}


def _mock_collection_info_response():
    return {"id": "sentinel-2-l2a", "title": "Sentinel-2 L2A"}


class TestQaSummary:
    """Phase 5: --qa sidecar summary tests for stac-search."""

    def test_help_includes_qa_flag(self):
        """--qa should appear in --help output."""
        import subprocess
        script = os.path.join(PROJECT_ROOT, "stac-search.py")
        out = subprocess.run(
            [sys.executable, script, "--help"],
            capture_output=True, text=True, timeout=10,
        )
        assert "--qa" in (out.stdout + out.stderr)

    def test_write_qa_summary_search(self, tmp_path):
        """_write_qa_summary should record feature ids and action='search'."""
        qa_path = str(tmp_path / "search.qa.json")
        parsed = argparse.Namespace(
            preset="planetary-computer", place=None,
            datetime="2024-01-01/2024-12-31", limit=10,
            collection=None,  # not used by _write_qa_summary (uses resolved)
            bbox=None, max_cloud_cover=None,
            qa=qa_path,
        )
        resolved = {
            "endpoint": "https://planetarycomputer.microsoft.com/api/stac/v1",
            "collection": ["sentinel-2-l2a"],
            "bbox": [120.0, 30.0, 121.0, 31.0],
            "max_cloud_cover": None,
        }
        data = _mock_search_response()
        stac_search._write_qa_summary(parsed, resolved, data, "search")
        assert os.path.exists(qa_path)
        summary = json.load(open(qa_path, encoding="utf-8"))
        assert summary["skill"] == "stac-search"
        assert summary["command"] == "search"
        assert summary["endpoint"] == resolved["endpoint"]
        assert summary["preset"] == "planetary-computer"
        assert summary["datetime"] == "2024-01-01/2024-12-31"
        assert summary["bbox"] == [120.0, 30.0, 121.0, 31.0]
        assert summary["n_features"] == 2
        assert summary["feature_ids"] == ["S2A_20240101", "S2A_20240115"]
        assert "timestamp" in summary
        assert "version" in summary

    def test_write_qa_summary_list_collections(self, tmp_path):
        """_write_qa_summary should record collection ids for list_collections."""
        qa_path = str(tmp_path / "list.qa.json")
        parsed = argparse.Namespace(
            preset="planetary-computer", place=None,
            datetime=None, limit=10, qa=qa_path,
        )
        resolved = {"endpoint": "https://example.com/stac"}
        data = _mock_list_collections_response()
        stac_search._write_qa_summary(parsed, resolved, data, "list_collections")
        summary = json.load(open(qa_path, encoding="utf-8"))
        assert summary["command"] == "list_collections"
        assert summary["n_collections"] == 2
        assert "sentinel-2-l2a" in summary["collection_ids"]

    def test_write_qa_summary_collection_info(self, tmp_path):
        """_write_qa_summary should record info_id / info_title for collection_info."""
        qa_path = str(tmp_path / "info.qa.json")
        parsed = argparse.Namespace(
            preset="planetary-computer", place=None,
            datetime=None, limit=10, qa=qa_path,
        )
        resolved = {"endpoint": "https://example.com/stac"}
        data = {"type": "CollectionInfo", "info": _mock_collection_info_response()}
        stac_search._write_qa_summary(parsed, resolved, data, "collection_info")
        summary = json.load(open(qa_path, encoding="utf-8"))
        assert summary["command"] == "collection_info"
        assert summary["info_id"] == "sentinel-2-l2a"
        assert summary["info_title"] == "Sentinel-2 L2A"

    def test_write_qa_summary_creates_parent_dir(self, tmp_path):
        """_write_qa_summary should create the parent directory if missing."""
        qa_path = str(tmp_path / "deep" / "nested" / "run.qa.json")
        parsed = argparse.Namespace(
            preset=None, place=None, datetime=None, limit=10, qa=qa_path,
        )
        resolved = {"endpoint": "https://example.com/stac"}
        stac_search._write_qa_summary(
            parsed, resolved,
            {"type": "FeatureCollection", "features": []},
            "search",
        )
        assert os.path.exists(qa_path)
