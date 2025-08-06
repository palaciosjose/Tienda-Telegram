import sqlite3
from datetime import datetime
import files
import db

class StatisticsManager:
    def __init__(self, db_path, shop_id=1):
        self.db_path = db_path
        self.shop_id = shop_id

    def _get_connection(self):
        if self.db_path == files.main_db:
            return db.get_db_connection(), True
        return sqlite3.connect(self.db_path), False

    def log_send(self, campaign_id, group_id, platform, success, result):
        conn, shared = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """INSERT INTO send_logs (campaign_id, group_id, platform, status, sent_date, error_message, shop_id)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                campaign_id,
                group_id,
                platform,
                'sent' if success else 'failed',
                datetime.now().isoformat(),
                '' if success else result,
                self.shop_id,
            )
        )
        conn.commit()
        if not shared:
            conn.close()

    def get_real_time_dashboard(self):
        conn, shared = self._get_connection()
        cursor = conn.cursor()
        today = datetime.now().strftime('%Y-%m-%d')
        cursor.execute(
            """SELECT COUNT(*), SUM(CASE WHEN status = 'sent' THEN 1 ELSE 0 END),
                      SUM(CASE WHEN platform = 'telegram' THEN 1 ELSE 0 END)
               FROM send_logs WHERE DATE(sent_date) = ? AND shop_id = ?""",
            (today, self.shop_id)
        )
        stats = cursor.fetchone()
        success_rate = (stats[1] / stats[0] * 100) if stats[0] else 0
        dashboard = (
            f"📊 **Dashboard de Marketing - {today}**\n\n"
            f"📤 **Mensajes enviados:** {stats[0]}\n"
            f"✅ **Exitosos:** {stats[1]} ({success_rate:.1f}%)\n"
            f"❌ **Fallidos:** {stats[0] - stats[1]}\n\n"
            f"📱 **Por plataforma:**\n- Telegram: {stats[2]}"
        )
        if not shared:
            conn.close()
        return dashboard
