#!/usr/bin/env python3
import time
import subprocess
import sys
import os
from datetime import datetime

# Cambiar al directorio del script
script_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(script_dir)

# Forzar logs al archivo directamente
log_file = os.path.join(script_dir, 'advertising.log')

def log_message(msg):
    with open(log_file, 'a') as f:
        f.write(f"{msg}\n")
        f.flush()
    print(msg)  # También imprimir a stdout

log_message(f"🚀 Advertising Daemon iniciado: {datetime.now()}")

while True:
    try:
        log_message(f"⏰ Ejecutando advertising_cron.py: {datetime.now()}")
        
        # Ejecutar advertising_cron.py
        result = subprocess.run([
            '/usr/bin/python3',
            'advertising_cron.py'
        ], capture_output=True, text=True, cwd=script_dir)
        
        if result.returncode == 0:
            log_message(f"✅ Advertising ejecutado correctamente")
            if result.stdout:
                log_message(f"   Output: {result.stdout.strip()}")
        else:
            log_message(f"❌ Error en advertising: {result.stderr}")
            
    except Exception as e:
        log_message(f"❌ Error inesperado: {e}")
    
    # Esperar 60 segundos antes de la próxima ejecución
    log_message(f"😴 Esperando 60 segundos...")
    time.sleep(60)