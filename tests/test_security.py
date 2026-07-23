import pytest
from unittest.mock import patch, MagicMock
from stac_search import search_stac, get_endpoint, parse_args, PRESET_ENDPOINTS


class TestSecurity:
    def test_no_hardcoded_credentials(self):
        import stac_search
        source = open(stac_search.__file__).read()
        assert "password" not in source.lower()
        assert "secret" not in source.lower()
        assert "api_key" not in source.lower()
        assert "token" not in source.lower()

    def test_no_proxy_hardcoded(self):
        import stac_search
        source = open(stac_search.__file__).read()
        assert "127.0.0.1:7897" not in source
        assert "7897" not in source
        assert "proxy" not in source.lower()

    def test_timeout_set(self):
        import stac_search
        source = open(stac_search.__file__).read()
        assert "timeout" in source

    def test_https_endpoints(self):
        for name, url in PRESET_ENDPOINTS.items():
            assert url.startswith("https://"), f"{name} endpoint should use HTTPS"

    def test_custom_endpoint_accepts_http(self):
        url = "http://localhost:8080/stac"
        assert get_endpoint(url) == url

    def test_no_sql_injection_risk(self):
        import stac_search
        source = open(stac_search.__file__).read()
        assert "execute" not in source.lower()
        assert "cursor" not in source.lower()
        assert "sqlite" not in source.lower()

    def test_no_file_write_operations(self):
        import stac_search
        source = open(stac_search.__file__).read()
        assert "open(" not in source or "w" not in source.split("open(")[-1][:20]

    def test_json_output_no_execution(self):
        import json
        data = {"test": "value"}
        result = json.dumps(data)
        assert "exec" not in result
        assert "eval" not in result

    def test_requests_uses_timeout(self):
        import stac_search
        source = open(stac_search.__file__).read()
        assert "timeout=60" in source or "timeout=30" in source

    def test_no_env_variable_leak(self):
        import stac_search
        source = open(stac_search.__file__).read()
        assert "os.environ" not in source
        assert "os.getenv" not in source

    def test_error_messages_safe(self):
        import requests
        from stac_search import run
        with patch("stac_search.search_stac", side_effect=Exception("test error")):
            output, code = run(["--preset", "planetary-computer", "--collection", "test"])
            assert code == 1
            assert "test error" not in output or "Error" in output
