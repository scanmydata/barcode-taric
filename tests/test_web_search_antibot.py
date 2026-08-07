from __future__ import annotations

from barcodetaric.engine import web_search


def test_cloudscraper_tier_is_graceful_when_dependency_missing(monkeypatch):
    monkeypatch.setattr(web_search, "_try_import_cloudscraper", lambda: None)

    results = web_search._via_cloudscraper("coffee 500ml", 3)

    assert results == []


def test_cloudscraper_tier_forwards_captcha_config(monkeypatch):
    class DummyResponse:
        text = ""

        def raise_for_status(self):
            return None

    class DummySession:
        def __init__(self):
            self.calls = []

        def get(self, url, timeout=None, headers=None):
            self.calls.append((url, timeout, headers))
            return DummyResponse()

    captured = {}

    class DummyScraperModule:
        @staticmethod
        def create_scraper(**kwargs):
            captured.update(kwargs)
            return DummySession()

    monkeypatch.setattr(web_search, "_try_import_cloudscraper", lambda: DummyScraperModule)
    monkeypatch.setattr(web_search, "SETTINGS", {
        "cloudscraper_enabled": True,
        "cloudscraper_browser": "chrome",
        "cloudscraper_timeout": 20,
        "captcha_solver": "capsolver",
        "captcha_provider_api_key": "secret-key",
    })
    monkeypatch.setattr(web_search, "debug", lambda *args, **kwargs: None)

    results = web_search._via_cloudscraper("coffee 500ml", 3)

    assert results == []
    assert captured["captcha"] == {"provider": "capsolver", "api_key": "secret-key"}


def test_open_websearch_parses_array(monkeypatch):
    captured = {}

    def fake_http_json(url, method=None, body=None, timeout=None, headers=None):
        captured["url"] = url
        captured["method"] = method
        captured["body"] = body
        return [
            {"title": "Nescafe Classic", "url": "https://x/1", "description": "<b>instant</b> coffee"},
            {"title": "T2", "url": "https://x/2", "snippet": "more"},
        ]

    monkeypatch.setattr(web_search, "SETTINGS", {"open_websearch_url": "http://localhost:3000"})
    monkeypatch.setattr(web_search, "http_json", fake_http_json)
    monkeypatch.setattr(web_search, "debug", lambda *a, **k: None)

    results = web_search._via_open_websearch("nescafe", 5)

    assert captured["url"] == "http://localhost:3000/search"
    assert captured["method"] == "POST" and captured["body"]["query"] == "nescafe"
    assert results[0]["title"] == "Nescafe Classic"
    assert results[0]["snippet"] == "instant coffee"   # tags stripped


def test_open_websearch_skips_without_url(monkeypatch):
    monkeypatch.setattr(web_search, "SETTINGS", {})
    assert web_search._via_open_websearch("x", 3) == []
