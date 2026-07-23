import pytest
from unittest.mock import patch, MagicMock
from stac_search import list_assets, format_assets_list, search_stac


class TestNoDownloadFunctionality:
    """Verify this is a search-only tool with no download capabilities."""

    def test_no_download_function_exists(self):
        import stac_search
        assert not hasattr(stac_search, "download_asset")
        assert not hasattr(stac_search, "download_file")

    def test_assets_are_search_results_only(self, sample_feature):
        assets = list_assets(sample_feature)
        for name, asset in assets.items():
            assert "href" in asset
            assert asset["href"].startswith("https://")

    def test_format_assets_shows_urls(self, sample_feature):
        result = format_assets_list(sample_feature)
        assert "https://example.com/B04.tif" in result
        assert "https://example.com/B03.tif" in result

    @patch("stac_search.requests.post")
    def test_search_returns_asset_urls(self, mock_post, mock_response, sample_search_response):
        mock_post.return_value = mock_response(sample_search_response)
        data = search_stac("https://example.com/stac", collections=["test"])
        feature = data["features"][0]
        assets = feature.get("assets", {})
        for name, asset in assets.items():
            assert asset["href"].startswith("https://")

    def test_asset_href_is_url(self, sample_feature):
        assets = sample_feature.get("assets", {})
        for name, asset in assets.items():
            href = asset.get("href", "")
            assert href.startswith("http://") or href.startswith("https://")

    def test_no_download_in_module(self):
        import stac_search
        source = open(stac_search.__file__ if hasattr(stac_search, "__file__") else "").read() if hasattr(stac_search, "__file__") else ""
        assert "download" not in dir(stac_search)
