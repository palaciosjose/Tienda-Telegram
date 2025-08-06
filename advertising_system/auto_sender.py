#!/usr/bin/env python3
import os
import time
import sqlite3
import logging
import re
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple

from .scheduler import CampaignScheduler
from .rate_limiter import IntelligentRateLimiter
from .statistics import StatisticsManager
from .telegram_multi import TelegramMultiBot


class AutoSender:
    def __init__(self, config: dict, shop_id: int = 1):
        self.config = config
        self.db_path = config['db_path']
        self.telegram_tokens = config.get('telegram_tokens', [])
        self.shop_id = shop_id if shop_id else config.get('shop_id', 1)
        
        self.scheduler = CampaignScheduler(self.db_path, shop_id=self.shop_id)
        self.rate_limiter = IntelligentRateLimiter(self.db_path, shop_id=self.shop_id)
        self.stats = StatisticsManager(self.db_path, shop_id=self.shop_id)
        self.logger = logging.getLogger(__name__)
        
        self.telegram = None
        self._init_telegram()

    def _init_telegram(self):
        tokens = self.telegram_tokens
        if not tokens:
            tokens_env = os.getenv("TELEGRAM_TOKEN")
            if tokens_env:
                tokens = [t.strip() for t in tokens_env.split(',') if t.strip()]
        
        if tokens:
            self.telegram = TelegramMultiBot(tokens)
        else:
            self.logger.warning("No hay tokens de Telegram configurados")

    def process_campaigns(self) -> bool:
        try:
            processed = self._check_and_send_campaigns()
            return processed
        except Exception as e:
            self.logger.error(f"Error procesando campañas: {e}")
            return False

    def _check_and_send_campaigns(self) -> bool:
        try:
            pending_sends = self.scheduler.get_pending_sends()
            
            if not pending_sends:
                return False
            
            processed = False
            for send_data in pending_sends:
                try:
                    schedule_id = send_data[0]
                    campaign_id = send_data[1]
                    platforms_str = send_data[5] if len(send_data) > 5 else None
                    
                    if not platforms_str:
                        continue
                    
                    platforms = platforms_str.split(',')
                    
                    for platform in platforms:
                        platform = platform.strip()
                        if platform == 'telegram':
                            success = self._send_telegram_campaign_corrected(campaign_id, schedule_id, send_data)
                            if success:
                                processed = True
                            time.sleep(2)
                    
                except Exception as e:
                    self.logger.error(f"Error procesando envío {send_data}: {e}")
                    continue
                    
            return processed
            
        except Exception as e:
            self.logger.error(f"Error en _check_and_send_campaigns: {e}")
            return False

    def _send_telegram_campaign_corrected(self, campaign_id: int, schedule_id: int, send_data: List) -> bool:
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Obtener grupos
            group_ids_str = None
            if len(send_data) > 10:
                potential = send_data[10]
                if potential is None or re.fullmatch(r"[0-9,]+", str(potential)):
                    group_ids_str = potential

            if group_ids_str:
                ids = [int(gid) for gid in group_ids_str.split(',') if gid.strip()]
                placeholders = ','.join('?' for _ in ids)
                query = (
                    'SELECT group_id, topic_id FROM target_groups '
                    'WHERE status = "active" AND shop_id = ? AND id IN (' + placeholders + ')'
                )
                cursor.execute(query, [self.shop_id, *ids])
            else:
                cursor.execute(
                    'SELECT group_id, topic_id FROM target_groups WHERE status = "active" AND shop_id = ?',
                    (self.shop_id,)
                )
            groups = cursor.fetchall()
            
            if not groups:
                print("❌ No hay grupos configurados")
                conn.close()
                return False
            
            # Obtener campaña
            cursor.execute('SELECT * FROM campaigns WHERE id = ?', (campaign_id,))
            campaign = cursor.fetchone()
            
            if not campaign:
                print(f"❌ Campaña {campaign_id} no encontrada")
                conn.close()
                return False
            
            campaign_name = campaign[1].replace('Producto ', '')  # QUITAR PREFIJO
            
            # BÚSQUEDA DE PRODUCTO
            cursor.execute('SELECT name, description, price, media_file_id, media_type FROM goods WHERE shop_id = ? AND name = ?', (self.shop_id, campaign_name))
            product = cursor.fetchone()
            
            if not product:
                cursor.execute('SELECT name, description, price, media_file_id, media_type FROM goods WHERE shop_id = ? AND name LIKE ?', (self.shop_id, f'%{campaign_name}%'))
                product = cursor.fetchone()
            
            if product:
                # USAR DATOS DE PRODUCTO
                title = f"🛒 {product[0]}"
                message_parts = [title]
                if product[1]:
                    message_parts.append(f"📝 {product[1]}")
                if product[2]:
                    message_parts.append(f"💰 Precio: ${product[2]}")
                full_message = '\n'.join(message_parts)
                media_file_id = product[3]
                media_type = product[4]
                print(f"✅ USANDO DATOS DE PRODUCTO: {product[0]}")
            else:
                # USAR DATOS DE CAMPAÑA
                title = campaign[1]
                message_text = campaign[2]
                full_message = f"📢 {title}\n\n{message_text}" if message_text else f"📢 {title}"
                media_file_id = campaign[3]
                media_type = campaign[4]
                print(f"✅ USANDO DATOS DE CAMPAÑA: {title}")
            
            # Obtener tokens
            tokens = self.telegram_tokens
            if not tokens:
                tokens_env = os.getenv("TELEGRAM_TOKEN")
                if not tokens_env:
                    print("❌ No hay tokens de Telegram configurados")
                    conn.close()
                    return False
                tokens = [t.strip() for t in tokens_env.split(',') if t.strip()]
            telegram_bot = TelegramMultiBot(tokens)
            
            # Preparar botones
            buttons = None
            if len(campaign) > 6 and campaign[6] and len(campaign) > 7 and campaign[7]:
                buttons = {
                    'button1_text': campaign[6],
                    'button1_url': campaign[7]
                }
            
            # ENVIAR A GRUPOS
            sent_count = 0
            for group in groups:
                try:
                    group_id, topic_id = group

                    success, result = telegram_bot.send_message(
                        group_id,
                        full_message,
                        media_file_id=media_file_id,
                        media_type=media_type,
                        buttons=buttons,
                        topic_id=topic_id,
                    )
                    
                    if success:
                        sent_count += 1
                        if product:
                            print(f'🎉 CAMPAÑA DE PRODUCTO {campaign_id} ENVIADA A {group_id}')
                        else:
                            print(f'🎉 CAMPAÑA NORMAL {campaign_id} ENVIADA A {group_id}')
                    else:
                        print(f'❌ Error enviando campaña {campaign_id} a {group_id}: {result}')
                        
                except Exception as e:
                    print(f'❌ Error enviando a grupo {group_id}: {e}')
                    continue
            
            if sent_count > 0:
                self.scheduler.update_next_send(schedule_id, 'telegram')
                conn.close()
                return True
            
            conn.close()
            return False
            
        except Exception as e:
            print(f"❌ Error en _send_telegram_campaign_corrected: {e}")
            return False

    def _send_telegram_campaign(self, campaign_id, schedule_id, send_data):
        """Backward compatible wrapper for `_send_telegram_campaign_corrected`."""
        return self._send_telegram_campaign_corrected(campaign_id, schedule_id, send_data)

    def start(self) -> bool:
        print(f"AutoSender iniciado: {datetime.now()}")
        return self.process_campaigns()