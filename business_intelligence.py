import db
from utils.ascii_chart import sparkline


def generate_bi_report():
    """Generate a simple Business Intelligence report.

    The report compares all stores computing a basic ROI (based on revenue),
    creates a ranking and shows the sales trend using ASCII sparklines.

    Returns:
        str: Multi-line textual summary.
    """
    con = db.get_db_connection()
    cur = con.cursor()
    try:
        cur.execute("SELECT id, name FROM shops")
        shops = cur.fetchall()
    except Exception:
        shops = []

    stats = []
    for sid, name in shops:
        try:
            cur.execute(
                "SELECT COALESCE(SUM(price),0) FROM purchases WHERE shop_id=?",
                (sid,),
            )
            revenue = cur.fetchone()[0] or 0
        except Exception:
            revenue = 0

        # Placeholder for costs; none are tracked currently
        cost = 0
        roi = revenue - cost

        sales_ts = db.get_sales_timeseries(store_id=sid)
        trend = sparkline([s["total"] for s in sales_ts]) if sales_ts else None

        stats.append({
            "shop_id": sid,
            "name": name,
            "roi": roi,
            "revenue": revenue,
            "trend": trend,
        })

    ranking = sorted(stats, key=lambda x: x["roi"], reverse=True)

    lines = ["📊 *Reporte BI*", ""]
    for idx, r in enumerate(ranking, 1):
        line = f"{idx}. {r['name']} - ROI: {r['roi']}"
        if r["trend"]:
            line += f" ({r['trend']})"
        lines.append(line)
    return "\n".join(lines)
