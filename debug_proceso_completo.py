import os
from datetime import datetime
from dotenv import load_dotenv
from advertising_system.auto_sender import AutoSender
from advertising_system.scheduler import CampaignScheduler

load_dotenv()

print(f"=== DEBUG PROCESO COMPLETO - {datetime.now()} ===")

# 1. Verificar scheduler
scheduler = CampaignScheduler('data/db/main_data.db', shop_id=1)
pending_sends = scheduler.get_pending_sends()
print(f"1. Programaciones pendientes: {len(pending_sends)}")

if not pending_sends:
    print("❌ No hay programaciones pendientes - STOP")
    exit()

# 2. Analizar datos de la programación
send_data = pending_sends[0]
print(f"2. Send data length: {len(send_data)}")
print(f"   Campaign ID: {send_data[1]}")
print(f"   Platforms: {send_data[5]}")

# 3. Crear AutoSender
token = os.getenv("TELEGRAM_TOKEN")
if not token:
    raise RuntimeError("Set TELEGRAM_TOKEN environment variable with your bot token")

config = {
    'db_path': 'data/db/main_data.db',
    'telegram_tokens': [token],
    'shop_id': 1
}
auto_sender = AutoSender(config)

# 4. Verificar grupos
groups = auto_sender._get_telegram_groups()
print(f"3. Grupos disponibles: {len(groups)}")

# 5. Simular _send_telegram_campaign manualmente
if groups:
    group = groups[0]
    print(f"4. Enviando a grupo: {group['group_name']}")
    
    # Verificar rate limit
    can_send, reason = auto_sender.rate_limiter.can_send('telegram')
    print(f"5. ¿Puede enviar? {can_send} - {reason}")
    
    if can_send:
        # Construir mensaje con índices corregidos
        message_data = {
            'message': send_data[11],
            'media_file_id': send_data[12],
            'media_type': send_data[13],
            'buttons': {
                'button1_text': send_data[14],
                'button1_url': send_data[15],
                'button2_text': send_data[16],
                'button2_url': send_data[17]
            }
        }
        
        print(f"6. Mensaje a enviar: {message_data['message'][:50]}...")
        print(f"   Media: {message_data['media_type']}")
        print(f"   Button1: {message_data['buttons']['button1_text']}")
        
        # Intentar envío real
        success, result = auto_sender.telegram.send_message(
            group['group_id'],
            message_data['message'],
            media_file_id=message_data['media_file_id'],
            media_type=message_data['media_type'],
            buttons=message_data['buttons']
        )
        
        print(f"7. ✅ RESULTADO FINAL:")
        print(f"   Success: {success}")
        print(f"   Result: {result}")
        
        if success:
            print("🎉 ¡EL ENVÍO FUNCIONÓ!")
        else:
            print("❌ Error en el envío")
    else:
        print(f"❌ Rate limit impide envío: {reason}")
else:
    print("❌ No hay grupos disponibles")
