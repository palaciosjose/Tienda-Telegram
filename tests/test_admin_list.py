from tests.test_categories import setup_dop


def test_get_adminlist_cleans_invalid(monkeypatch, tmp_path):
    dop = setup_dop(monkeypatch, tmp_path)
    admins_file = tmp_path / "admins_list.txt"
    admins_file.write_text("123\nabc\n456\n")
    monkeypatch.setattr(dop.files, "admins_list", str(admins_file))

    admins = dop.get_adminlist()

    assert admins == [1, 123, 456]
    assert admins_file.read_text().splitlines() == ["123", "456"]

