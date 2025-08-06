#!/bin/bash
echo "🔄 Reiniciando bot..."
pkill -f "python3.*main.py"
rm -f data/bot.pid
sleep 2
nohup python3 main.py > bot.log 2>&1 &
sleep 2
echo "✅ Bot reiniciado (Puerto 8444)"
echo "📱 Prueba /start en Telegram"
