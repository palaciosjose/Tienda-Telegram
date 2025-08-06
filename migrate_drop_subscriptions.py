#!/usr/bin/env python3
"""Drop obsolete subscription tables from the database."""

import sqlite3
import db


def main():
    conn = db.get_db_connection()
    cur = conn.cursor()

    cur.execute("DROP TABLE IF EXISTS user_subscriptions")
    cur.execute("DROP TABLE IF EXISTS subscription_products")

    try:
        cur.execute("DROP INDEX IF EXISTS idx_user_subscriptions_end_date")
    except sqlite3.Error:
        pass

    conn.commit()
    print("✓ Tablas de suscripciones eliminadas")


if __name__ == "__main__":
    main()

