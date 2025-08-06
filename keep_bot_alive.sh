#!/bin/bash
while true; do
    if ! pgrep -f "python3.*webhook_server.py" > /dev/null; then
        echo "Bot detenido - Reiniciando webhook_server.py... $(date)" >> bot_restart.log
        cd /home/serverbussn/prueba.sdpro.shop
        # Inicia webhook_server.py que usará la configuración de config.py (puerto 8444)
        nohup python3 webhook_server.py >> webhook_server.log 2>&1 &
    fi
    sleep 30
done
