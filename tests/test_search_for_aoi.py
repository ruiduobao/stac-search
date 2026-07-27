"""test_search_for_aoi.py — Phase 1+ unified STAC API 测试"""
import os
import sys
import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, PROJECT_ROOT)

import stac_search


def test_search_for_aoi_validates_inputs():
    """没有 aoi_manifest 也没有 bbox → ValueError"""
    with pytest.raises(ValueError, match="must provide"):
        stac_search.search_stac_for_aoi()


def test_search_for_aoi_validates_bbox_shape():
    """bbox 长度不是 4 → ValueError"""
    with pytest.raises(ValueError, match="must be"):
        stac_search.search_stac_for_aoi(bbox=(1, 2, 3))


def test_search_for_aoi_extracts_bbox_from_manifest():
    """从 aoi_manifest dict 提取 bbox_wgs84"""
    captured = {}
    def mock_search_stac(*args, **kwargs):
        captured["bbox"] = kwargs.get("bbox")
        captured["endpoint"] = kwargs.get("endpoint")
        return {"type": "FeatureCollection", "features": []}

    import unittest.mock as mock
    with mock.patch.object(stac_search, "search_stac", side_effect=mock_search_stac):
        m = {"query": "北京", "bbox_wgs84": [115.7, 39.4, 116.7, 40.2]}
        result = stac_search.search_stac_for_aoi(m)
    assert captured["bbox"] == (115.7, 39.4, 116.7, 40.2)
    assert result["type"] == "FeatureCollection"


def test_search_for_aoi_explicit_bbox_overrides():
    """显式 bbox 优先于 aoi_manifest"""
    captured = {}
    def mock_search_stac(*args, **kwargs):
        captured["bbox"] = kwargs.get("bbox")
        return {"type": "FeatureCollection", "features": []}

    import unittest.mock as mock
    with mock.patch.object(stac_search, "search_stac", side_effect=mock_search_stac):
        m = {"bbox_wgs84": [0, 0, 1, 1]}
        stac_search.search_stac_for_aoi(m, bbox=(100, 30, 110, 40))
    assert captured["bbox"] == (100, 30, 110, 40)


def test_search_for_aoi_passes_through_kwargs():
    """collections / datetime_range / max_cloud_cover 透传"""
    captured = {}
    def mock_search_stac(*args, **kwargs):
        captured.update(kwargs)
        return {"type": "FeatureCollection", "features": []}

    import unittest.mock as mock
    with mock.patch.object(stac_search, "search_stac", side_effect=mock_search_stac):
        stac_search.search_stac_for_aoi(
            bbox=(115, 39, 117, 41),
            collections=["landsat-c2-l2"],
            datetime_range="2024-06-01/2024-08-31",
            limit=5,
            max_cloud_cover=15.0,
        )
    assert captured["collections"] == ["landsat-c2-l2"]
    assert captured["datetime_range"] == "2024-06-01/2024-08-31"
    assert captured["limit"] == 5
    assert captured["max_cloud_cover"] == 15.0
