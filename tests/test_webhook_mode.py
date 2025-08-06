import pytest
from tests.test_shop_info import setup_main


def test_run_webhook_requires_url(monkeypatch, tmp_path):
    dop, main, calls, bot = setup_main(monkeypatch, tmp_path)
    monkeypatch.setattr(main.config, "WEBHOOK_URL", "")
    with pytest.raises(RuntimeError):
        main.run_webhook()
