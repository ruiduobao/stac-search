import importlib.util
import json
import sys
from pathlib import Path
import pytest

# Load stac-search.py as stac_search module
_script_path = Path(__file__).parent.parent / "stac-search.py"
_spec = importlib.util.spec_from_file_location("stac_search", _script_path)
_stac_search = importlib.util.module_from_spec(_spec)
sys.modules["stac_search"] = _stac_search
_spec.loader.exec_module(_stac_search)

from stac_search import (
    get_endpoint,
    search_stac,
    list_collections,
    get_collection_info,
    list_assets,
    format_results_table,
    format_assets_list,
    parse_args,
    run,
    PRESET_ENDPOINTS,
    DEFAULT_COLLECTIONS,
)


@pytest.fixture
def sample_feature():
    return {
        "id": "S2A_MSIL2A_20240101T000000_N0000_R001",
        "type": "Feature",
        "bbox": [120.0, 30.0, 121.0, 31.0],
        "properties": {
            "datetime": "2024-01-01T00:00:00Z",
            "eo:cloud_cover": 15.5,
            "collection": "sentinel-2-l2a",
        },
        "assets": {
            "B04": {"href": "https://example.com/B04.tif", "type": "image/tiff", "roles": ["data"]},
            "B03": {"href": "https://example.com/B03.tif", "type": "image/tiff", "roles": ["data"]},
            "thumbnail": {"href": "https://example.com/thumb.png", "type": "image/png", "roles": ["thumbnail"]},
        },
    }


@pytest.fixture
def sample_search_response(sample_feature):
    return {
        "type": "FeatureCollection",
        "features": [sample_feature],
        "links": [],
        "numberMatched": 1,
        "numberReturned": 1,
    }


@pytest.fixture
def sample_collection():
    return {
        "id": "sentinel-2-l2a",
        "title": "Sentinel-2 Level-2A",
        "description": "Sentinel-2 Level-2A surface reflectance data",
        "license": "proprietary",
        "extent": {
            "spatial": {"bbox": [[-180, -90, 180, 90]]},
            "temporal": {"interval": [["2015-07-01T00:00:00Z", None]]},
        },
    }


@pytest.fixture
def sample_collections_list(sample_collection):
    return [sample_collection]


@pytest.fixture
def mock_response():
    class MockResponse:
        def __init__(self, json_data, status_code=200):
            self._json = json_data
            self.status_code = status_code
            self.text = json.dumps(json_data)

        def json(self):
            return self._json

        def raise_for_status(self):
            if self.status_code >= 400:
                from requests.exceptions import HTTPError
                raise HTTPError(f"HTTP {self.status_code}", response=self)

    return MockResponse
