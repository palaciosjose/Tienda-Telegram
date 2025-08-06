import sqlite3
import json
from datetime import datetime, timedelta
import files
import db

class CampaignScheduler:

    # Mapeo de días español-inglés
    SPANISH_DAYS = {
        'lunes': 'monday',
        'martes': 'tuesday', 
        'miércoles': 'wednesday',
        'miercoles': 'wednesday',
        'jueves': 'thursday',
        'viernes': 'friday',
        'sábado': 'saturday',
        'sabado': 'saturday',
        'domingo': 'sunday'
    }
    
    def normalize_day(self, day):
        """Convertir día español a inglés si es necesario"""
        day_lower = day.lower().strip()
        return self.SPANISH_DAYS.get(day_lower, day_lower)

    def __init__(self, db_path, shop_id=1):
        self.db_path = db_path
        self.shop_id = shop_id
        self.optimal_times = ['10:00', '15:00', '20:00']
        self.platform_delays = {
            'telegram': 60
        }

    def _get_connection(self):
        if self.db_path == files.main_db:
            return db.get_db_connection(), True
        return sqlite3.connect(self.db_path), False

    def create_daily_schedule(self, campaign_id, platforms=['telegram']):
        conn, shared = self._get_connection()
        cursor = conn.cursor()

        for platform in platforms:
            cursor.execute(
                "SELECT COUNT(*) FROM target_groups WHERE platform = ? AND status = 'active' AND shop_id = ?",
                (platform, self.shop_id)
            )
            group_count = cursor.fetchone()[0]
            if group_count == 0:
                continue

            groups_per_time = group_count // len(self.optimal_times)

            for i, send_time in enumerate(self.optimal_times):
                start_groups = i * groups_per_time
                end_groups = start_groups + groups_per_time
                estimated_duration = groups_per_time * (self.platform_delays[platform] / 60)
                schedule_data = {
                    'campaign_id': campaign_id,
                    'platform': platform,
                    'schedule_json': json.dumps({d: [send_time] for d in ['monday','tuesday','wednesday','thursday','friday','saturday','sunday']}),
                    'group_range': f'{start_groups}-{end_groups}',
                    'estimated_duration': estimated_duration,
                    'shop_id': self.shop_id
                }
                self.save_schedule(schedule_data)

        if not shared:
            conn.close()

    def save_schedule(self, data):
        conn, shared = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """INSERT INTO campaign_schedules
               (campaign_id, schedule_name, frequency, schedule_json, target_platforms, created_date, shop_id, group_ids)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                data['campaign_id'],
                'auto',
                'daily',
                data['schedule_json'],
                data['platform'],
                datetime.now().isoformat(),
                data.get('shop_id', self.shop_id),
                ','.join(map(str, data.get('group_ids', []))) if data.get('group_ids') else None,
            )
        )
        conn.commit()
        if not shared:
            conn.close()

    def get_pending_sends(self):
        now = datetime.now()
        current_time = now.strftime('%H:%M')
        
        # Crear rango de ±2 minutos para matching más flexible
        time_range = []
        for offset in [-2, -1, 0, 1, 2]:
            time_check = (now + timedelta(minutes=offset)).strftime('%H:%M')
            time_range.append(time_check)
        
        conn, shared = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """SELECT cs.*, c.name, c.message_text, c.media_file_id, c.media_type,
                       c.button1_text, c.button1_url, c.button2_text, c.button2_url
                   FROM campaign_schedules cs
                   JOIN campaigns c ON cs.campaign_id = c.id
                   WHERE cs.is_active = 1 AND c.status = 'active' AND cs.shop_id = ? AND c.shop_id = ?""",
            (self.shop_id, self.shop_id),
        )
        rows = cursor.fetchall()
        pending = []
        day_map = ['lunes', 'martes', 'miercoles', 'jueves', 'viernes', 'sabado', 'domingo']
        today = day_map[now.weekday()]
        for row in rows:
            try:
                schedule = json.loads(row[4] or '{}')
            except Exception:
                continue
            next_send = row[7] if len(row) > 7 else None
            if next_send:
                try:
                    if datetime.fromisoformat(next_send) > now:
                        continue
                except Exception:
                    pass
            # Buscar en el rango de tiempo en lugar de hora exacta
            if any(t in schedule.get(today, []) for t in time_range):
                pending.append(row)

        if not shared:
            conn.close()
        return pending

    def update_next_send(self, schedule_id, platform):
        from datetime import datetime, timedelta
        import json
        
        conn, shared = self._get_connection()
        cursor = conn.cursor()
        
        # Obtener programación actual
        cursor.execute("SELECT schedule_json FROM campaign_schedules WHERE id = ?", (schedule_id,))
        result = cursor.fetchone()
        if not result:
            if not shared:
                conn.close()
            return
            
        schedule = json.loads(result[0])
        now = datetime.now()
        day_map = ['lunes', 'martes', 'miercoles', 'jueves', 'viernes', 'sabado', 'domingo']
        today = day_map[now.weekday()]
        
        # Buscar próxima hora de envío
        next_send = None
        if today in schedule:
            current_time = now.strftime('%H:%M')
            future_times = [t for t in schedule[today] if t > current_time]
            if future_times:
                # Hay más envíos hoy
                next_time = min(future_times)
                next_send = now.replace(hour=int(next_time[:2]), minute=int(next_time[3:]), second=0, microsecond=0)
            else:
                # No hay más envíos hoy, próximo será mañana
                next_send = now + timedelta(days=1)
                next_send = next_send.replace(hour=0, minute=0, second=0, microsecond=0)
        
        if platform == 'telegram' and next_send:
            cursor.execute(
                "UPDATE campaign_schedules SET next_send_telegram = ? WHERE id = ?",
                (next_send.isoformat(), schedule_id))
        conn.commit()
        if not shared:
            conn.close()

    def update_schedule(self, schedule_id, days=None, times=None, platforms=None, group_ids=None):
        """Modificar una programación existente."""
        conn, shared = self._get_connection()
        cursor = conn.cursor()

        fields = []
        params = []

        if days is not None or times is not None:
            schedule = {}
            if days is None:
                days = []
            norm_days = [self.normalize_day(d) for d in days]
            for d in norm_days:
                schedule[d] = times or []
            fields.append("schedule_json = ?")
            params.append(json.dumps(schedule))

        if platforms is not None:
            fields.append("target_platforms = ?")
            params.append(','.join(platforms))

        if group_ids is not None:
            fields.append("group_ids = ?")
            params.append(','.join(map(str, group_ids)) if group_ids else None)

        if not fields:
            if not shared:
                conn.close()
            return False

        params.extend([schedule_id, self.shop_id])
        cursor.execute(
            f"UPDATE campaign_schedules SET {', '.join(fields)} WHERE id = ? AND shop_id = ?",
            params,
        )
        conn.commit()
        success = cursor.rowcount > 0
        if not shared:
            conn.close()
        return success

    def _reindex_schedules(self, cursor):
        cursor.execute(
            "SELECT id FROM campaign_schedules WHERE shop_id = ? ORDER BY id",
            (self.shop_id,),
        )
        ids = [r[0] for r in cursor.fetchall()]
        for idx, old_id in enumerate(ids, start=1):
            if old_id != idx:
                cursor.execute(
                    "UPDATE campaign_schedules SET id = ? WHERE id = ?",
                    (-idx, old_id),
                )
        for idx, old_id in enumerate(ids, start=1):
            if old_id != idx:
                cursor.execute(
                    "UPDATE campaign_schedules SET id = ? WHERE id = ?",
                    (idx, -idx),
                )

    def delete_schedule(self, schedule_id):
        """Eliminar una programación y reindexar"""
        conn, shared = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "DELETE FROM campaign_schedules WHERE id = ? AND shop_id = ?",
            (schedule_id, self.shop_id),
        )
        deleted = cursor.rowcount > 0
        if deleted:
            self._reindex_schedules(cursor)
        conn.commit()
        if not shared:
            conn.close()
        return deleted