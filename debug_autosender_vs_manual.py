import os
from datetime import datetime
from dotenv import load_dotenv
from advertising_system.auto_sender import AutoSender

load_dotenv()

print(f"=== COMPARACIÓN: AutoSender Real vs Manual - {datetime.now()} ===")

# Obtener el token desde la variable de entorno
token = os.getenv("TELEGRAM_TOKEN")
if not token:
    raise RuntimeError("Set TELEGRAM_TOKEN environment variable with your bot token")

config = {
    'db_path': 'data/db/main_data.db',
    'telegram_tokens': [token],
    'shop_id': 1
}

auto_sender = AutoSender(config)

print("1. Ejecutando _check_and_send_campaigns (como hace el cron real)...")

# Simular exactamente lo que hace el cron
pending_sends = auto_sender.scheduler.get_pending_sends()
print(f"   Pending sends encontrados: {len(pending_sends)}")

processed = False
for send_data in pending_sends:
    schedule_id = send_data[0]
    campaign_id = send_data[1]
    platforms = send_data[5].split(',')  # Corregido
    
    print(f"   Procesando Campaign ID: {campaign_id}")
    print(f"   Platforms: {platforms}")
    
    for platform in platforms:
        print(f"   Procesando platform: {platform}")
        if platform == 'telegram':
            print("   ✅ Platform es telegram, llamando _send_telegram_campaign...")
            
            # Aquí está la clave: llamar al método real
            try:
                auto_sender._send_telegram_campaign(campaign_id, schedule_id, send_data)
                print("   ✅ _send_telegram_campaign ejecutado sin errores")
                processed = True
            except Exception as e:
                print(f"   ❌ ERROR en _send_telegram_campaign: {e}")
                import traceback
                traceback.print_exc()
            
            import time
            time.sleep(2)

print(f"2. ¿Processed? {processed}")

if processed:
    print("🎉 AutoSender real debería haber enviado")
else:
    print("❌ AutoSender real NO procesó nada")
