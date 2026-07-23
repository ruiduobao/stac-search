import pytest
from unittest.mock import patch, MagicMock
import json
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
)


class TestIntegrationSearchWorkflow:
    @patch("stac_search.requests.post")
    def test_full_search_workflow(self, mock_post, mock_response, sample_search_response):
        mock_post.return_value = mock_response(sample_search_response)
        endpoint = get_endpoint("planetary-computer")
        data = search_stac(endpoint, collections=["sentinel-2-l2a"], bbox=(120, 30, 121, 31), limit=5)
        assert data["type"] == "FeatureCollection"
        table = format_results_table(data)
        assert "Found 1 item(s)" in table

    @patch("stac_search.requests.post")
    def test_search_and_list_assets(self, mock_post, mock_response, sample_search_response):
        mock_post.return_value = mock_response(sample_search_response)
        data = search_stac("https://example.com/stac", collections=["test"])
        assets_output = format_assets_list(data["features"][0])
        assert "B04" in assets_output

    @patch("stac_search.requests.post")
    def test_search_json_roundtrip(self, mock_post, mock_response, sample_search_response):
        mock_post.return_value = mock_response(sample_search_response)
        data = search_stac("https://example.com/stac", collections=["test"])
        json_str = json.dumps(data, indent=2)
        parsed = json.loads(json_str)
        assert parsed == data

    @patch("stac_search.requests.get")
    @patch("stac_search.requests.post")
    def test_list_then_search(self, mock_post, mock_get, mock_response, sample_search_response, sample_collections_list):
        mock_get.return_value = mock_response({"collections": sample_collections_list})
        mock_post.return_value = mock_response(sample_search_response)
        collections = list_collections("https://example.com/stac")
        assert len(collections) > 0
        data = search_stac("https://example.com/stac", collections=[collections[0]["id"]])
        assert len(data["features"]) > 0

    @patch("stac_search.requests.get")
    def test_collection_info_workflow(self, mock_get, mock_response, sample_collection):
        mock_get.return_value = mock_response(sample_collection)
        info = get_collection_info("https://example.com/stac", "sentinel-2-l2a")
        assert info["id"] == "sentinel-2-l2a"
        assert "Sentinel-2" in info["title"]

    @patch("stac_search.search_stac")
    def test_run_full_workflow(self, mock_search, sample_search_response):
        mock_search.return_value = sample_search_response
        output, code = run(["--preset", "planetary-computer", "--collection", "sentinel-2-l2a", "--bbox", "120", "30", "121", "31", "--limit", "5", "--json"])
        assert code == 0
        data = json.loads(output)
        assert data["type"] == "FeatureCollection"

    @patch("stac_search.search_stac")
    def test_run_with_all_filters(self, mock_search, sample_search_response):
        mock_search.return_value = sample_search_response
        output, code = run([
            "--preset", "planetary-computer",
            "--collection", "sentinel-2-l2a",
            "--bbox", "120", "30", "121", "31",
            "--datetime", "2024-01-01/2024-12-31",
            "--max-cloud-cover", "20",
            "--limit", "5",
        ])
        assert code == 0

    @patch("stac_search.search_stac")
    def test_run_output_formats(self, mock_search, sample_search_response):
        mock_search.return_value = sample_search_response
        output_text, _ = run(["--preset", "planetary-computer", "--collection", "test"])
        output_json, _ = run(["--preset", "planetary-computer", "--collection", "test", "--json"])
        assert "Found" in output_text
        assert json.loads(output_json)

    @patch("stac_search.search_stac")
    def test_run_multiple_collections(self, mock_search, sample_search_response):
        mock_search.return_value = sample_search_response
        output, code = run(["--preset", "planetary-computer", "--collection", "sentinel-2-l2a", "landsat-c2-l2", "--json"])
        assert code == 0

    @patch("stac_search.search_stac")
    def test_run_gee_preset(self, mock_search, sample_search_response):
        mock_search.return_value = sample_search_response
        output, code = run(["--preset", "gee", "--collection", "COPERNICUS/S2_SR_HARMONIZED", "--json"])
        assert code == 0

    @patch("stac_search.search_stac")
    def test_run_element84_preset(self, mock_search, sample_search_response):
        mock_search.return_value = sample_search_response
        output, code = run(["--preset", "element84", "--collection", "sentinel-2-l2a", "--json"])
        assert code == 0

    @patch("stac_search.search_stac")
    def test_run_custom_endpoint(self, mock_search, sample_search_response):
        mock_search.return_value = sample_search_response
        output, code = run(["--endpoint", "https://custom-stac.example.com/v1", "--collection", "test", "--json"])
        assert code == 0

    @patch("stac_search.search_stac")
    def test_run_error_recovery(self, mock_search):
        import requests
        mock_search.side_effect = requests.ConnectionError()
        output, code = run(["--preset", "planetary-computer", "--collection", "test"])
        assert code == 1
        assert "Error" in output

    @patch("stac_search.search_stac")
    def test_run_list_assets_workflow(self, mock_search, sample_search_response):
        mock_search.return_value = sample_search_response
        output, code = run(["--preset", "planetary-computer", "--collection", "test", "--list-assets", "--json"])
        assert code == 0

    def test_all_presets_have_valid_urls(self):
        for name, url in PRESET_ENDPOINTS.items():
            assert url.startswith("https://")
            assert "/stac" in url or "/v1" in url or "/catalog" in url
