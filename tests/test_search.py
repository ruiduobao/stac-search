import pytest
from unittest.mock import patch, MagicMock
import requests
from stac_search import (
    get_endpoint,
    search_stac,
    list_collections,
    get_collection_info,
    list_assets,
    format_results_table,
    format_assets_list,
    PRESET_ENDPOINTS,
)


class TestGetEndpoint:
    def test_preset_planetary_computer(self):
        assert get_endpoint("planetary-computer") == PRESET_ENDPOINTS["planetary-computer"]

    def test_preset_aws_earth_search(self):
        assert get_endpoint("aws-earth-search") == PRESET_ENDPOINTS["aws-earth-search"]

    def test_preset_element84(self):
        assert get_endpoint("element84") == PRESET_ENDPOINTS["element84"]

    def test_preset_gee(self):
        assert get_endpoint("gee") == PRESET_ENDPOINTS["gee"]

    def test_custom_url(self):
        url = "https://custom-stac.example.com/v1"
        assert get_endpoint(url) == url

    def test_custom_url_http(self):
        url = "http://localhost:8080/stac"
        assert get_endpoint(url) == url


class TestSearchStac:
    @patch("stac_search.requests.post")
    def test_basic_search(self, mock_post, mock_response, sample_search_response):
        mock_post.return_value = mock_response(sample_search_response)
        result = search_stac("https://example.com/stac", collections=["test"])
        assert result["type"] == "FeatureCollection"
        assert len(result["features"]) == 1

    @patch("stac_search.requests.post")
    def test_search_with_bbox(self, mock_post, mock_response, sample_search_response):
        mock_post.return_value = mock_response(sample_search_response)
        result = search_stac("https://example.com/stac", bbox=(120, 30, 121, 31))
        call_kwargs = mock_post.call_args
        assert call_kwargs[1]["json"]["bbox"] == [120, 30, 121, 31]

    @patch("stac_search.requests.post")
    def test_search_with_datetime(self, mock_post, mock_response, sample_search_response):
        mock_post.return_value = mock_response(sample_search_response)
        search_stac("https://example.com/stac", datetime_range="2024-01-01/2024-12-31")
        call_kwargs = mock_post.call_args
        assert call_kwargs[1]["json"]["datetime"] == "2024-01-01/2024-12-31"

    @patch("stac_search.requests.post")
    def test_search_with_cloud_cover(self, mock_post, mock_response, sample_search_response):
        mock_post.return_value = mock_response(sample_search_response)
        search_stac("https://example.com/stac", max_cloud_cover=20)
        call_kwargs = mock_post.call_args
        assert call_kwargs[1]["json"]["query"] == {"eo:cloud_cover": {"lte": 20}}

    @patch("stac_search.requests.post")
    def test_search_with_limit(self, mock_post, mock_response, sample_search_response):
        mock_post.return_value = mock_response(sample_search_response)
        search_stac("https://example.com/stac", limit=5)
        call_kwargs = mock_post.call_args
        assert call_kwargs[1]["json"]["limit"] == 5

    @patch("stac_search.requests.post")
    def test_search_default_limit(self, mock_post, mock_response, sample_search_response):
        mock_post.return_value = mock_response(sample_search_response)
        search_stac("https://example.com/stac")
        call_kwargs = mock_post.call_args
        assert call_kwargs[1]["json"]["limit"] == 10

    @patch("stac_search.requests.post")
    def test_search_with_custom_query(self, mock_post, mock_response, sample_search_response):
        mock_post.return_value = mock_response(sample_search_response)
        custom_query = {"eo:cloud_cover": {"lte": 30}}
        search_stac("https://example.com/stac", query=custom_query)
        call_kwargs = mock_post.call_args
        assert call_kwargs[1]["json"]["query"] == custom_query

    @patch("stac_search.requests.post")
    def test_search_http_error(self, mock_post):
        resp = MagicMock()
        resp.status_code = 400
        resp.text = "Bad Request"
        mock_post.return_value = resp
        mock_post.return_value.raise_for_status.side_effect = requests.HTTPError(response=resp)
        with pytest.raises(requests.HTTPError):
            search_stac("https://example.com/stac")

    @patch("stac_search.requests.post")
    def test_search_connection_error(self, mock_post):
        mock_post.side_effect = requests.ConnectionError()
        with pytest.raises(requests.ConnectionError):
            search_stac("https://example.com/stac")

    @patch("stac_search.requests.post")
    def test_search_timeout(self, mock_post):
        mock_post.side_effect = requests.Timeout()
        with pytest.raises(requests.Timeout):
            search_stac("https://example.com/stac")

    @patch("stac_search.requests.post")
    def test_search_url_construction(self, mock_post, mock_response, sample_search_response):
        mock_post.return_value = mock_response(sample_search_response)
        search_stac("https://example.com/stac/v1", collections=["test"])
        call_args = mock_post.call_args
        assert call_args[0][0] == "https://example.com/stac/v1/search"

    @patch("stac_search.requests.post")
    def test_search_url_trailing_slash(self, mock_post, mock_response, sample_search_response):
        mock_post.return_value = mock_response(sample_search_response)
        search_stac("https://example.com/stac/v1/", collections=["test"])
        call_args = mock_post.call_args
        assert call_args[0][0] == "https://example.com/stac/v1/search"


class TestListCollections:
    @patch("stac_search.requests.get")
    def test_list_collections_success(self, mock_get, mock_response, sample_collections_list):
        mock_get.return_value = mock_response({"collections": sample_collections_list})
        result = list_collections("https://example.com/stac")
        assert len(result) == 1
        assert result[0]["id"] == "sentinel-2-l2a"

    @patch("stac_search.requests.get")
    def test_list_collections_empty(self, mock_get, mock_response):
        mock_get.return_value = mock_response({"collections": []})
        result = list_collections("https://example.com/stac")
        assert result == []

    @patch("stac_search.requests.get")
    def test_list_collections_no_key(self, mock_get, mock_response):
        mock_get.return_value = mock_response({})
        result = list_collections("https://example.com/stac")
        assert result == []

    @patch("stac_search.requests.get")
    def test_list_collections_http_error(self, mock_get):
        resp = MagicMock()
        resp.status_code = 500
        resp.text = "Internal Server Error"
        mock_get.return_value = resp
        mock_get.return_value.raise_for_status.side_effect = requests.HTTPError(response=resp)
        with pytest.raises(requests.HTTPError):
            list_collections("https://example.com/stac")


class TestGetCollectionInfo:
    @patch("stac_search.requests.get")
    def test_get_collection_info_success(self, mock_get, mock_response, sample_collection):
        mock_get.return_value = mock_response(sample_collection)
        result = get_collection_info("https://example.com/stac", "sentinel-2-l2a")
        assert result["id"] == "sentinel-2-l2a"
        assert result["title"] == "Sentinel-2 Level-2A"

    @patch("stac_search.requests.get")
    def test_get_collection_info_not_found(self, mock_get):
        resp = MagicMock()
        resp.status_code = 404
        resp.text = "Not Found"
        mock_get.return_value = resp
        mock_get.return_value.raise_for_status.side_effect = requests.HTTPError(response=resp)
        with pytest.raises(requests.HTTPError):
            get_collection_info("https://example.com/stac", "nonexistent")

    @patch("stac_search.requests.get")
    def test_get_collection_info_url(self, mock_get, mock_response, sample_collection):
        mock_get.return_value = mock_response(sample_collection)
        get_collection_info("https://example.com/stac", "test-collection")
        call_args = mock_get.call_args
        assert call_args[0][0] == "https://example.com/stac/collections/test-collection"


class TestListAssets:
    def test_list_assets_from_properties(self, sample_feature):
        assets = list_assets(sample_feature)
        assert "B04" in assets
        assert "B03" in assets

    def test_list_assets_empty(self):
        item = {"id": "test", "properties": {}, "assets": {}}
        assets = list_assets(item)
        assert assets == {}

    def test_list_assets_no_assets(self):
        item = {"id": "test", "properties": {}}
        assets = list_assets(item)
        assert assets == {}


class TestFormatResultsTable:
    def test_format_results_with_data(self, sample_search_response):
        result = format_results_table(sample_search_response)
        assert "Found 1 item(s)" in result
        assert "S2A_MSIL2A_20240101T000000" in result
        assert "sentinel-2-l2a" in result

    def test_format_results_empty(self):
        data = {"features": []}
        result = format_results_table(data)
        assert "No results found" in result

    def test_format_results_verbose(self, sample_search_response):
        result = format_results_table(sample_search_response, verbose=True)
        assert "B04" in result
        assert "image/tiff" in result

    def test_format_results_no_bbox(self):
        data = {
            "features": [
                {
                    "id": "test",
                    "properties": {"datetime": "2024-01-01", "eo:cloud_cover": 10, "collection": "test"},
                }
            ]
        }
        result = format_results_table(data)
        assert "N/A" in result

    def test_format_results_cloud_cover(self, sample_search_response):
        result = format_results_table(sample_search_response)
        assert "15.5%" in result

    def test_format_results_multiple(self, sample_feature):
        data = {
            "features": [
                {**sample_feature, "id": "item1"},
                {**sample_feature, "id": "item2"},
            ]
        }
        result = format_results_table(data)
        assert "Found 2 item(s)" in result
        assert "item1" in result
        assert "item2" in result


class TestFormatAssetsList:
    def test_format_assets(self, sample_feature):
        result = format_assets_list(sample_feature)
        assert "B04" in result
        assert "B03" in result
        assert "thumbnail" in result

    def test_format_assets_no_assets(self):
        item = {"id": "test", "assets": {}}
        result = format_assets_list(item)
        assert "No assets found" in result

    def test_format_assets_with_roles(self, sample_feature):
        result = format_assets_list(sample_feature)
        assert "data" in result
        assert "thumbnail" in result

    def test_format_assets_href(self, sample_feature):
        result = format_assets_list(sample_feature)
        assert "https://example.com/B04.tif" in result
