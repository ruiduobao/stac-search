import pytest
import sys
from unittest.mock import patch, MagicMock
from stac_search import parse_args, run, PRESET_ENDPOINTS


class TestParseArgs:
    def test_preset_only(self):
        args = parse_args(["--preset", "planetary-computer", "--collection", "sentinel-2-l2a"])
        assert args.preset == "planetary-computer"
        assert args.collection == ["sentinel-2-l2a"]

    def test_endpoint_only(self):
        args = parse_args(["--endpoint", "https://example.com/stac", "--collection", "test"])
        assert args.endpoint == "https://example.com/stac"

    def test_list_collections(self):
        args = parse_args(["--list-collections", "--preset", "aws-earth-search"])
        assert args.list_collections is True
        assert args.preset == "aws-earth-search"

    def test_collection_info(self):
        args = parse_args(["--collection-info", "sentinel-2-l2a", "--preset", "planetary-computer"])
        assert args.collection_info == "sentinel-2-l2a"

    def test_bbox(self):
        args = parse_args(["--preset", "planetary-computer", "--collection", "test", "--bbox", "120", "30", "121", "31"])
        assert args.bbox == [120.0, 30.0, 121.0, 31.0]

    def test_datetime(self):
        args = parse_args(["--preset", "planetary-computer", "--collection", "test", "--datetime", "2024-01-01/2024-12-31"])
        assert args.datetime == "2024-01-01/2024-12-31"

    def test_max_cloud_cover(self):
        args = parse_args(["--preset", "planetary-computer", "--collection", "test", "--max-cloud-cover", "20"])
        assert args.max_cloud_cover == 20.0

    def test_limit(self):
        args = parse_args(["--preset", "planetary-computer", "--collection", "test", "--limit", "5"])
        assert args.limit == 5

    def test_json_output(self):
        args = parse_args(["--preset", "planetary-computer", "--collection", "test", "--json"])
        assert args.json is True

    def test_verbose(self):
        args = parse_args(["--preset", "planetary-computer", "--collection", "test", "--verbose"])
        assert args.verbose is True

    def test_list_assets(self):
        args = parse_args(["--preset", "planetary-computer", "--collection", "test", "--list-assets"])
        assert args.list_assets is True

    def test_multiple_collections(self):
        args = parse_args(["--preset", "planetary-computer", "--collection", "sentinel-2-l2a", "landsat-c2-l2"])
        assert args.collection == ["sentinel-2-l2a", "landsat-c2-l2"]

    def test_default_limit(self):
        args = parse_args(["--preset", "planetary-computer", "--collection", "test"])
        assert args.limit == 10

    def test_all_presets_valid(self):
        for preset in PRESET_ENDPOINTS:
            args = parse_args(["--preset", preset, "--collection", "test"])
            assert args.preset == preset


class TestRun:
    @patch("stac_search.search_stac")
    def test_run_search_success(self, mock_search, sample_search_response):
        mock_search.return_value = sample_search_response
        output, code = run(["--preset", "planetary-computer", "--collection", "sentinel-2-l2a", "--json"])
        assert code == 0
        assert "S2A_MSIL2A_20240101T000000" in output

    @patch("stac_search.list_collections")
    def test_run_list_collections(self, mock_list, sample_collections_list):
        mock_list.return_value = sample_collections_list
        output, code = run(["--list-collections", "--preset", "planetary-computer"])
        assert code == 0
        assert "sentinel-2-l2a" in output

    @patch("stac_search.get_collection_info")
    def test_run_collection_info(self, mock_info, sample_collection):
        mock_info.return_value = sample_collection
        output, code = run(["--collection-info", "sentinel-2-l2a", "--preset", "planetary-computer"])
        assert code == 0
        assert "sentinel-2-l2a" in output

    @patch("stac_search.search_stac")
    def test_run_search_text_output(self, mock_search, sample_search_response):
        mock_search.return_value = sample_search_response
        output, code = run(["--preset", "planetary-computer", "--collection", "sentinel-2-l2a"])
        assert code == 0
        assert "Found 1 item(s)" in output

    @patch("stac_search.search_stac")
    def test_run_list_assets(self, mock_search, sample_search_response):
        mock_search.return_value = sample_search_response
        output, code = run(["--preset", "planetary-computer", "--collection", "sentinel-2-l2a", "--list-assets"])
        assert code == 0
        assert "B04" in output

    @patch("stac_search.search_stac")
    def test_run_verbose(self, mock_search, sample_search_response):
        mock_search.return_value = sample_search_response
        output, code = run(["--preset", "planetary-computer", "--collection", "sentinel-2-l2a", "--verbose"])
        assert code == 0
        assert "B04" in output

    @patch("stac_search.search_stac")
    def test_run_connection_error(self, mock_search):
        import requests
        mock_search.side_effect = requests.ConnectionError()
        output, code = run(["--preset", "planetary-computer", "--collection", "test"])
        assert code == 1
        assert "Connection Error" in output

    @patch("stac_search.search_stac")
    def test_run_timeout(self, mock_search):
        import requests
        mock_search.side_effect = requests.Timeout()
        output, code = run(["--preset", "planetary-computer", "--collection", "test"])
        assert code == 1
        assert "Timeout" in output

    @patch("stac_search.search_stac")
    def test_run_http_error(self, mock_search):
        import requests
        resp = MagicMock()
        resp.status_code = 404
        resp.text = "Not Found"
        mock_search.side_effect = requests.HTTPError(response=resp)
        output, code = run(["--preset", "planetary-computer", "--collection", "test"])
        assert code == 1
        assert "HTTP Error" in output

    @patch("stac_search.search_stac")
    def test_run_json_output(self, mock_search, sample_search_response):
        mock_search.return_value = sample_search_response
        output, code = run(["--preset", "planetary-computer", "--collection", "test", "--json"])
        assert code == 0
        import json
        data = json.loads(output)
        assert data["type"] == "FeatureCollection"

    @patch("stac_search.search_stac")
    def test_run_no_results(self, mock_search):
        mock_search.return_value = {"type": "FeatureCollection", "features": []}
        output, code = run(["--preset", "planetary-computer", "--collection", "test"])
        assert code == 0
        assert "No results found" in output

    @patch("stac_search.search_stac")
    def test_run_list_assets_no_results(self, mock_search):
        mock_search.return_value = {"type": "FeatureCollection", "features": []}
        output, code = run(["--preset", "planetary-computer", "--collection", "test", "--list-assets"])
        assert code == 0
        assert "No results" in output

    @patch("stac_search.search_stac")
    def test_run_with_bbox(self, mock_search, sample_search_response):
        mock_search.return_value = sample_search_response
        output, code = run(["--preset", "planetary-computer", "--collection", "test", "--bbox", "120", "30", "121", "31", "--json"])
        assert code == 0

    @patch("stac_search.search_stac")
    def test_run_with_datetime(self, mock_search, sample_search_response):
        mock_search.return_value = sample_search_response
        output, code = run(["--preset", "planetary-computer", "--collection", "test", "--datetime", "2024-01-01/2024-12-31"])
        assert code == 0

    @patch("stac_search.search_stac")
    def test_run_with_cloud_cover(self, mock_search, sample_search_response):
        mock_search.return_value = sample_search_response
        output, code = run(["--preset", "planetary-computer", "--collection", "test", "--max-cloud-cover", "20"])
        assert code == 0
