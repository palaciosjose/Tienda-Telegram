import time
import sqlite3
from collections import defaultdict
from datetime import datetime
import files
import db

class IntelligentRateLimiter:
    def __init__(self, db_path, shop_id=1):
        self.db_path = db_path
        self.shop_id = shop_id
        self.platform_limits = {
            'telegram': {
                'messages_per_second': 30,
                'messages_per_minute': 1800,
                'messages_per_hour': 100000,
                'delay_between_groups': 1.0
            }
        }
        self.counters = defaultdict(lambda: defaultdict(int))
        self.last_reset = defaultdict(datetime.now)

    def _get_connection(self):
        if self.db_path == files.main_db:
            return db.get_db_connection(), True
        return sqlite3.connect(self.db_path), False

    def can_send(self, platform):
        now = datetime.now()
        limits = self.platform_limits[platform]
        if (now - self.last_reset[platform]).seconds >= 60:
            self.counters[platform]['minute'] = 0
            self.last_reset[platform] = now
        if (now - self.last_reset[platform]).seconds >= 3600:
            self.counters[platform]['hour'] = 0
        if self.counters[platform]['minute'] >= limits['messages_per_minute']:
            return False, "Límite por minuto alcanzado"
        if self.counters[platform]['hour'] >= limits['messages_per_hour']:
            return False, "Límite por hora alcanzado"
        return True, "OK"

    def register_send(self, platform, success=True):
        self.counters[platform]['minute'] += 1
        self.counters[platform]['hour'] += 1
        self.log_send_attempt(platform, success)

    def get_optimal_delay(self, platform, recent_failures=0):
        base_delay = self.platform_limits[platform]['delay_between_groups']
        if recent_failures > 0:
            return base_delay * (1 + recent_failures * 0.5)
        return base_delay

    def log_send_attempt(self, platform, success):
        conn, shared = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO rate_limit_logs (platform, success, timestamp, shop_id) VALUES (?, ?, ?, ?)",
            (platform, int(success), datetime.now().isoformat(), self.shop_id)
        )
        conn.commit()
        if not shared:
            conn.close()
