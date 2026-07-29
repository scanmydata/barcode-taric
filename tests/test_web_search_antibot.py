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
