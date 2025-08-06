#!/bin/bash
cd /home/serverbussn/prueba.sdpro.shop

# Matar proceso anterior si existe
pkill -f "python3.*main.py" 2>/dev/null || true

# Esperar un momento
sleep 2

# Iniciar bot en background
nohup python3 main.py >> bot.log 2>&1 &

echo "Bot iniciado - $(date)"
echo "PID: $!"
