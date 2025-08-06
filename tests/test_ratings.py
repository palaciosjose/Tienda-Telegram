import sqlite3
from tests.test_categories import setup_dop


def test_rating_average(monkeypatch, tmp_path):
    dop = setup_dop(monkeypatch, tmp_path)
    dop.ensure_database_schema()

    dop.submit_shop_rating(1, 1, 5)
    dop.submit_shop_rating(1, 2, 3)
    avg, count = dop.get_shop_rating(1)

    assert round(avg, 1) == 4.0
    assert count == 2

    # Reemplazar calificación del usuario 1
    dop.submit_shop_rating(1, 1, 1)
    avg, count = dop.get_shop_rating(1)
    assert round(avg, 1) == 2.0
    assert count == 2
