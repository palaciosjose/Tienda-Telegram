import pytest
from advertising_system.content_validator import ContentValidator


def test_rejects_forbidden_word():
    assert not ContentValidator.is_valid("This is spam")


def test_length_limit(monkeypatch):
    monkeypatch.setattr(ContentValidator, "max_length", 5)
    assert not ContentValidator.is_valid("123456")


def test_blacklisted_domain(monkeypatch):
    monkeypatch.setattr(ContentValidator, "blacklisted_domains", {"bad.com"})
    assert not ContentValidator.is_valid("Visit http://bad.com")


def test_strip_markup_allows_text():
    assert ContentValidator.is_valid("<b>Hello</b>", strip_markup=True)


def test_valid_text(monkeypatch):
    monkeypatch.setattr(ContentValidator, "max_length", 1000)
    monkeypatch.setattr(ContentValidator, "blacklisted_domains", set())
    assert ContentValidator.is_valid("Check https://example.com")

