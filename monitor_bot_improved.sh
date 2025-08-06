#!/bin/bash

BOT_DIR="/home/telegram-bot"
LOG_FILE="$BOT_DIR/monitor.log"
TOKEN="7275890221:AAFWOshIFIedAEHNatzQ53rgGwljvpow2cM"

log_msg() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

restart_bot() {
    log_msg "🔄 Reiniciando bot por problema detectado..."
    cd "$BOT_DIR"
    
    # Matar proceso anterior
    pkill -f "python3.*main.py" 2>/dev/null
    rm -f data/bot.pid
    sleep 3
    
    # Limpiar webhook
    curl -s "https://api.telegram.org/bot$TOKEN/deleteWebhook" > /dev/null
    sleep 2
    
    # Reiniciar bot
    nohup python3 main.py > bot.log 2>&1 &
    sleep 5
    
    # Reconfigurar webhook
    curl -s -F "url=https://5.189.170.98:8443/bot" \
         -F "certificate=@/etc/ssl/telegram-bot/cert.pem" \
         "https://api.telegram.org/bot$TOKEN/setWebhook" > /dev/null
    
    log_msg "✅ Bot reiniciado y webhook reconfigurado"
}

check_bot() {
    # 1. Verificar que el proceso existe
    if ! pgrep -f "python3.*main.py" > /dev/null; then
        log_msg "❌ Proceso no encontrado"
        return 1
    fi
    
    # 2. Verificar que responde a health check
    if ! curl -s -k --max-time 10 "https://127.0.0.1:8443/metrics" > /dev/null 2>&1; then
        log_msg "❌ Bot no responde a health check"
        return 1
    fi
    
    # 3. **NUEVO**: Verificar webhook en detalle
    webhook_info=$(curl -s "https://api.telegram.org/bot$TOKEN/getWebhookInfo")
    
    # Verificar si webhook está configurado
    webhook_url=$(echo "$webhook_info" | grep -o '"url":"[^"]*"' | cut -d'"' -f4)
    if [ "$webhook_url" != "https://5.189.170.98:8443/bot" ]; then
        log_msg "❌ Webhook mal configurado: $webhook_url"
        return 1
    fi
    
    # Verificar updates pendientes (si hay muchas, algo está mal)
    pending=$(echo "$webhook_info" | grep -o '"pending_update_count":[0-9]*' | cut -d: -f2)
    if [ "$pending" ] && [ "$pending" -gt 50 ]; then
        log_msg "⚠️ Demasiadas updates pendientes ($pending) - Webhook no procesa"
        return 1
    fi
    
    # Verificar último error
    last_error=$(echo "$webhook_info" | grep -o '"last_error_message":"[^"]*"' | cut -d'"' -f4)
    if [ "$last_error" ] && [ "$last_error" != "" ]; then
        log_msg "⚠️ Error en webhook: $last_error"
        return 1
    fi
    
    # 4. **NUEVO**: Verificar logs recientes por errores
    if [ -f bot.log ]; then
        # Buscar errores en los últimos 5 minutos
        recent_errors=$(tail -50 bot.log | grep -i "error\|exception\|failed" | wc -l)
        if [ "$recent_errors" -gt 3 ]; then
            log_msg "⚠️ Muchos errores recientes ($recent_errors) en bot.log"
            return 1
        fi
    fi
    
    return 0
}

log_msg "🚀 Monitor MEJORADO del bot iniciado"

while true; do
    if ! check_bot; then
        restart_bot
        
        # Esperar más tiempo después de reiniciar
        sleep 300  # 5 minutos
    else
        log_msg "✅ Bot verificado: proceso, health check, webhook y logs OK"
    fi
    
    # Verificar cada 2 minutos
    sleep 120
done
