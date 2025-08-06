import sqlite3
import json
import re
from datetime import datetime
import logging
import files
import db
from advertising_system.telegram_multi import TelegramMultiBot

class AdvertisingManager:
    def __init__(self, db_path, shop_id=1):
        self.db_path = db_path
        self.shop_id = shop_id
        self.logger = logging.getLogger(__name__)

    def _get_connection(self):
        if self.db_path == files.main_db:
            return db.get_db_connection(), True
        return sqlite3.connect(self.db_path), False

    def create_campaign(self, data):
        """Crear una nueva campaña"""
        conn, shared = self._get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT INTO campaigns (name, message_text, media_file_id, media_type, 
                                     button1_text, button1_url, button2_text, button2_url, 
                                     status, created_by, shop_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'active', ?, ?)
            """, (
                data.get('name'),
                data.get('message_text'),
                data.get('media_file_id'),
                data.get('media_type'),
                data.get('button1_text'),
                data.get('button1_url'),
                data.get('button2_text'),
                data.get('button2_url'),
                data.get('created_by'),
                self.shop_id
            ))
            
            campaign_id = cursor.lastrowid
            conn.commit()
            if not shared:
                conn.close()
            return campaign_id
        except Exception as e:
            if not shared:
                conn.close()
            self.logger.error(f"Error creating campaign: {e}")
            return None

    def get_all_campaigns(self):
        """Obtener todas las campañas"""
        conn, shared = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, name, status, created_date 
            FROM campaigns 
            WHERE shop_id = ? 
            ORDER BY created_date DESC
        """, (self.shop_id,))
        
        campaigns = []
        for row in cursor.fetchall():
            campaigns.append({
                'id': row[0],
                'name': row[1],
                'status': row[2],
                'created_date': row[3]
            })
        
        if not shared:
            conn.close()
        return campaigns

    def delete_campaign(self, campaign_id):
        """Eliminar una campaña"""
        conn, shared = self._get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("DELETE FROM campaigns WHERE id = ? AND shop_id = ?", (campaign_id, self.shop_id))
            success = cursor.rowcount > 0
            conn.commit()
            if not shared:
                conn.close()
            return success
        except Exception as e:
            if not shared:
                conn.close()
            self.logger.error(f"Error deleting campaign: {e}")
            return False

    def schedule_campaign(self, campaign_id, days, times, platforms=None, group_ids=None):
        """Programar una campaña para enviarse en días y horas específicas."""
        if platforms is None:
            platforms = ['telegram']

        # Mapeo español -> inglés
        spanish_to_english = {
            'lunes': 'monday', 'martes': 'tuesday', 'miercoles': 'wednesday',
            'jueves': 'thursday', 'viernes': 'friday', 'sabado': 'saturday', 'domingo': 'sunday'
        }

        # Convertir días españoles a ingleses
        converted_days = []
        for day in days:
            day_clean = day.strip().lower()
            if day_clean in spanish_to_english:
                converted_days.append(spanish_to_english[day_clean])
            elif day_clean in {'monday','tuesday','wednesday','thursday','friday','saturday','sunday'}:
                converted_days.append(day_clean)
            else:
                return False, f'Día inválido: {day}. Use: lunes, martes, miercoles, jueves, viernes, sabado, domingo'

        day_list = converted_days

        # Validar formato de horas
        for t in times:
            if not re.match(r'^\d{2}:\d{2}$', t):
                return False, 'Formato de hora inválido'

        # Pero guardar en español para que el cron lo encuentre
        spanish_days = {
            'monday': 'lunes', 'tuesday': 'martes', 'wednesday': 'miercoles',
            'thursday': 'jueves', 'friday': 'viernes', 'saturday': 'sabado', 'sunday': 'domingo'
        }
        
        schedule = {}
        for d in day_list:
            spanish_day = spanish_days.get(d, d)
            schedule[spanish_day] = times[:2]
        
        schedule_json = json.dumps(schedule)

        conn, shared = self._get_connection()
        cur = conn.cursor()
        cur.execute('SELECT 1 FROM campaigns WHERE id = ? AND shop_id = ?', (campaign_id, self.shop_id))
        if not cur.fetchone():
            if not shared:
                conn.close()
            return False, 'Campaña no encontrada'

        try:
            cur.execute(
                """INSERT INTO campaign_schedules
                   (campaign_id, schedule_name, frequency, schedule_json,
                    target_platforms, created_date, shop_id, group_ids)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    campaign_id,
                    'manual',
                    'weekly',
                    schedule_json,
                    ','.join(platforms),
                    datetime.now().isoformat(),
                    self.shop_id,
                    ','.join(map(str, group_ids)) if group_ids else None,
                ),
            )
            conn.commit()
            if not shared:
                conn.close()
            return True, 'Programación creada'
        except Exception as e:
            if not shared:
                conn.close()
            return False, str(e)

    def update_campaign(self, campaign_id, fields):
        """Actualizar una campaña existente"""
        conn, shared = self._get_connection()
        cursor = conn.cursor()
        
        # Construir la consulta dinámicamente
        set_clauses = []
        values = []
        
        for field, value in fields.items():
            if field in ['name', 'message_text', 'media_file_id', 'media_type', 
                        'button1_text', 'button1_url', 'button2_text', 'button2_url']:
                set_clauses.append(f"{field} = ?")
                values.append(value)
        
        if not set_clauses:
            if not shared:
                conn.close()
            return False
        
        values.extend([campaign_id, self.shop_id])
        query = f"UPDATE campaigns SET {', '.join(set_clauses)} WHERE id = ? AND shop_id = ?"
        
        try:
            cursor.execute(query, values)
            success = cursor.rowcount > 0
            conn.commit()
            if not shared:
                conn.close()
            return success
        except Exception as e:
            if not shared:
                conn.close()
            self.logger.error(f"Error updating campaign: {e}")
            return False

    def add_target_group(self, platform, group_id, group_name=None, topic_id=None):
        """Agregar un grupo objetivo"""
        conn, shared = self._get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute(
                """
                INSERT INTO target_groups (platform, group_id, group_name, topic_id, status, shop_id)
                VALUES (?, ?, ?, ?, 'active', ?)
                """,
                (platform, group_id, group_name, topic_id, self.shop_id),
            )
            
            conn.commit()
            if not shared:
                conn.close()
            return True, 'Grupo agregado correctamente'
        except sqlite3.IntegrityError:
            if not shared:
                conn.close()
            return False, 'El grupo ya existe'
        except Exception as e:
            if not shared:
                conn.close()
            return False, str(e)

    def remove_target_group(self, group_id):
        """Eliminar un grupo objetivo"""
        conn, shared = self._get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("DELETE FROM target_groups WHERE group_id = ? AND shop_id = ?", (group_id, self.shop_id))
            success = cursor.rowcount > 0
            conn.commit()
            if not shared:
                conn.close()
            return success, 'Grupo eliminado' if success else 'Grupo no encontrado'
        except Exception as e:
            if not shared:
                conn.close()
            return False, str(e)

    def get_target_groups(self):
        """Obtener grupos objetivo activos"""
        conn, shared = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, group_id, group_name, topic_id 
            FROM target_groups 
            WHERE status = 'active' AND shop_id = ?
        """, (self.shop_id,))
        
        groups = []
        for row in cursor.fetchall():
            groups.append({
                'id': row[0],
                'group_id': row[1],
                'group_name': row[2],
                'topic_id': row[3]
            })
        
        if not shared:
            conn.close()
        return groups

    def send_campaign_to_group(self, campaign_id, group_id, topic_id=None):
        """Enviar una campaña a un grupo específico"""
        try:
            import os
            
            tokens_env = os.getenv("TELEGRAM_TOKEN")
            if not tokens_env:
                return False, "No hay tokens de Telegram configurados"
            
            tokens = [t.strip() for t in tokens_env.split(',') if t.strip()]
            telegram = TelegramMultiBot(tokens)
            
            # Obtener datos de la campaña
            conn, shared = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT name, message_text, media_file_id, media_type,
                       button1_text, button1_url, button2_text, button2_url
                FROM campaigns 
                WHERE id = ? AND shop_id = ?
            """, (campaign_id, self.shop_id))
            
            campaign = cursor.fetchone()
            if not campaign:
                if not shared:
                    conn.close()
                return False, "Campaña no encontrada"
            
            name, message, media_file_id, media_type, btn1_text, btn1_url, btn2_text, btn2_url = campaign

            # Construir mensaje y botones
            full_message = message
            
            buttons = {}
            if btn1_text and btn1_url:
                buttons['button1_text'] = btn1_text
                buttons['button1_url'] = btn1_url
            if btn2_text and btn2_url:
                buttons['button2_text'] = btn2_text
                buttons['button2_url'] = btn2_url
            
            # Enviar mensaje
            send_kwargs = dict(
                media_file_id=media_file_id,
                media_type=media_type,
                buttons=buttons if buttons else None,
            )
            if topic_id is not None:
                send_kwargs["topic_id"] = topic_id
            success, result = telegram.send_message(
                group_id,
                full_message,
                **send_kwargs
            )
            
            # Log del envío
            cursor.execute(
                """INSERT INTO send_logs (campaign_id, group_id, platform, status, sent_date, error_message, shop_id)
                   VALUES (?, ?, 'telegram', ?, ?, ?, ?)""",
                (
                    campaign_id,
                    group_id,
                    'sent' if success else 'failed',
                    datetime.now().isoformat(),
                    None if success else result,
                    self.shop_id,
                ),
            )
            
            conn.commit()
            if not shared:
                conn.close()
            
            return success, result
            
        except Exception as e:
            self.logger.error(f"Error sending campaign: {e}")
            return False, str(e)

    def send_campaign_now(self, campaign_id, platforms=None):
        """Enviar una campaña inmediatamente a los grupos registrados."""
        if platforms is None:
            platforms = ["telegram"]

        overall_success = True
        last_msg = "Campaña enviada"

        if "telegram" in platforms:
            groups = self.get_target_groups()
            for g in groups:
                ok, msg = self.send_campaign_to_group(
                    campaign_id, g["group_id"], g.get("topic_id")
                )
                if not ok:
                    overall_success = False
                    last_msg = msg

        return overall_success, last_msg

    def get_today_stats(self):
        """Obtener estadísticas rápidas del día"""
        conn, shared = self._get_connection()
        cursor = conn.cursor()
        today = datetime.now().strftime('%Y-%m-%d')
        cursor.execute(
            "SELECT COUNT(*) FROM send_logs WHERE DATE(sent_date) = ? AND shop_id = ?",
            (today, self.shop_id),
        )
        sent = cursor.fetchone()[0]
        cursor.execute(
            "SELECT COUNT(*) FROM target_groups WHERE status = 'active' AND shop_id = ?",
            (self.shop_id,),
        )
        groups = cursor.fetchone()[0]
        if not shared:
            conn.close()
        return {
            'sent': sent,
            'success_rate': 100,
            'groups': groups
        }

    def get_platform_configs(self):
        """Obtener configuraciones de plataformas"""
        return [{'platform': 'telegram', 'is_active': True}]

    def update_platform_config(self, platform, **kwargs):
        """Actualizar configuración de plataforma"""
        return True

    def deactivate_schedule(self, schedule_id):
        """Desactivar una programación de campaña."""
        conn, shared = self._get_connection()
        cur = conn.cursor()
        cur.execute(
            "UPDATE campaign_schedules SET is_active = 0 WHERE id = ? AND shop_id = ?",
            (schedule_id, self.shop_id),
        )
        success = cur.rowcount > 0
        conn.commit()
        if not shared:
            conn.close()
        return success
