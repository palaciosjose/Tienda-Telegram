#!/bin/bash

BOT_DIR="/home/telegram-bot"
LOG_FILE="$BOT_DIR/monitor.log"

log_msg() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

restart_bot() {
    log_msg "🔄 Reiniciando bot..."
    cd "$BOT_DIR"
    
    # Matar proceso anterior
    pkill -f "python3.*main.py" 2>/dev/null
    rm -f data/bot.pid
    sleep 3
    
    # Reiniciar bot
    nohup python3 main.py > bot.log 2>&1 &
    sleep 5
    
    # Reconfigurar webhook
    curl -s -F "url=https://5.189.170.98:8443/bot" \
         -F "certificate=@/etc/ssl/telegram-bot/cert.pem" \
         "https://api.telegram.org/bot7275890221:AAFWOshIFIedAEHNatzQ53rgGwljvpow2cM/setWebhook" > /dev/null
    
    log_msg "✅ Bot reiniciado y webhook configurado"
}

check_bot() {
    # 1. Verificar que el proceso existe
    if ! pgrep -f "python3.*main.py" > /dev/null; then
        log_msg "❌ Proceso no encontrado"
        return 1
    fi
    
    # 2. Verificar que responde
    if ! curl -s -k --max-time 10 "https://127.0.0.1:8443/metrics" > /dev/null 2>&1; then
        log_msg "❌ Bot no responde a health check"
        return 1
    fi
    
    # 3. Verificar webhook (opcional)
    webhook_status=$(curl -s "https://api.telegram.org/bot7275890221:AAFWOshIFIedAEHNatzQ53rgGwljvpow2cM/getWebhookInfo" | grep -o '"pending_update_count":[0-9]*' | cut -d: -f2)
    
    if [ "$webhook_status" ] && [ "$webhook_status" -gt 100 ]; then
        log_msg "⚠️ Muchas updates pendientes ($webhook_status) - Reiniciando..."
        return 1
    fi
    
    return 0
}

log_msg "🚀 Monitor del bot iniciado"

while true; do
    if ! check_bot; then
        restart_bot
    else
        log_msg "✅ Bot funcionando correctamente"
    fi
    
    # Verificar cada 2 minutos
    sleep 120
done
