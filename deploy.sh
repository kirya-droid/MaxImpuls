#!/bin/bash
# 🚀 Скрипт для деплоя на сервер

SERVER="root@vm3591453"
REMOTE_PATH="/home/ImpulsBot"

echo "🚀 Начинаем деплой..."

# Копируем файлы
scp -r \
    tk_scanner/ \
    tk_dashboard/ \
    main.py \
    requirements.txt \
    .env \
    $SERVER:$REMOTE_PATH/

echo "✅ Файлы скопированы"

# Перезапускаем сервис
ssh $SERVER << 'ENDSSH'
    cd $REMOTE_PATH
    pip3 install -r requirements.txt --quiet
    systemctl daemon-reload
    systemctl restart tk_scanner
    echo "✅ Сервис перезапущен"
ENDSSH

echo "🎉 Деплой завершён!"
