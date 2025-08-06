import types, builtins, os, shelve
from tests.test_shop_info import setup_main


def test_missing_temp_file_resets_state(monkeypatch, tmp_path):
    dop, main, calls, _ = setup_main(monkeypatch, tmp_path)
    dop.ensure_database_schema()

    monkeypatch.setattr(dop, "get_adminlist", lambda: [1])
    monkeypatch.setattr(main.adminka.dop, "get_adminlist", lambda: [1])
    monkeypatch.setattr(main.adminka.files, "sost_bd", str(tmp_path / "sost.bd"))

    with shelve.open(main.adminka.files.sost_bd) as bd:
        bd["1"] = 8

    def fake_open(file, *a, **k):
        if file == "data/Temp/1.txt":
            raise FileNotFoundError
        return builtins.open(file, *a, **k)

    monkeypatch.setattr(builtins, "open", fake_open)

    main.adminka.text_analytics("desc", 1)

    with shelve.open(main.adminka.files.sost_bd) as bd:
        assert "1" not in bd


def test_invalid_quantity_resets_state(monkeypatch, tmp_path):
    dop, main, calls, _ = setup_main(monkeypatch, tmp_path)
    dop.ensure_database_schema()

    monkeypatch.setattr(dop, "get_adminlist", lambda: [1])
    monkeypatch.setattr(main.adminka.dop, "get_adminlist", lambda: [1])
    monkeypatch.setattr(main.adminka.files, "sost_bd", str(tmp_path / "sost.bd"))

    os.makedirs("data/Temp", exist_ok=True)
    with builtins.open("data/Temp/1_product.txt", "w", encoding="utf-8") as f:
        f.write("Item")

    with shelve.open(main.adminka.files.sost_bd) as bd:
        bd["1"] = 183

    main.adminka.text_analytics("abc", 1)

    with shelve.open(main.adminka.files.sost_bd) as bd:
        assert "1" not in bd
