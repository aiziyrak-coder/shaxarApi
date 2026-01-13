#!/bin/bash
# ============================================
# 🛑 PERMANENT FIX: Disable All Conflicting Bots
# ============================================

echo "=========================================="
echo "🛑 DISABLING CONFLICTING BOTS PERMANENTLY"
echo "=========================================="
echo ""

# 1. Stop and disable systemd services
echo "=== 1. Systemd Services ==="
systemctl stop cdquizbot 2>/dev/null && echo "  ✅ Stopped cdquizbot"
systemctl disable cdquizbot 2>/dev/null && echo "  ✅ Disabled cdquizbot"
systemctl mask cdquizbot 2>/dev/null && echo "  ✅ Masked cdquizbot (prevents restart)"

# 2. Rename conflicting directories
echo ""
echo "=== 2. Conflicting Directories ==="

if [ -d "/var/opt/smartFrontFull" ]; then
    mv /var/opt/smartFrontFull "/var/opt/smartFrontFull.DISABLED.$(date +%Y%m%d_%H%M%S)"
    echo "  ✅ Disabled /var/opt/smartFrontFull"
fi

if [ -d "/var/opt/smartApiFull" ]; then
    mv /var/opt/smartApiFull "/var/opt/smartApiFull.DISABLED.$(date +%Y%m%d_%H%M%S)"
    echo "  ✅ Disabled /var/opt/smartApiFull"
fi

if [ -d "/opt/cdquizbot" ]; then
    mv /opt/cdquizbot "/opt/cdquizbot.DISABLED.$(date +%Y%m%d_%H%M%S)"
    echo "  ✅ Disabled /opt/cdquizbot"
fi

# 3. Check cron jobs
echo ""
echo "=== 3. Cron Jobs ==="
if crontab -l 2>/dev/null | grep -i bot; then
    echo "  ⚠️ Found bot cron jobs - remove them manually:"
    crontab -l | grep -i bot
else
    echo "  ✅ No bot cron jobs found"
fi

# 4. Check rc.local
echo ""
echo "=== 4. RC.local ==="
if [ -f /etc/rc.local ] && grep -i bot /etc/rc.local; then
    echo "  ⚠️ Found bot in rc.local - remove manually"
else
    echo "  ✅ No bot in rc.local"
fi

# 5. Kill ALL existing bots
echo ""
echo "=== 5. Killing All Bots ==="
pkill -9 -f "bot.py" && echo "  ✅ Killed all bot.py processes"
pkill -9 -f "iot_monitor" && echo "  ✅ Killed all iot_monitor processes"

# Wait for processes to fully terminate
sleep 5

# Double check
if ps aux | grep -E "bot.py|iot_monitor" | grep -v grep > /dev/null; then
    echo "  ⚠️ Some processes still running:"
    ps aux | grep -E "bot.py|iot_monitor" | grep -v grep
else
    echo "  ✅ All bot processes killed"
fi

# 6. Wait for Telegram to release connection
echo ""
echo "=== 6. Waiting for Telegram API (60 seconds) ==="
for i in {60..1}; do
    printf "\r  Waiting: %02d seconds remaining..." $i
    sleep 1
done
echo ""
echo "  ✅ Wait complete"

# 7. Start our bot
echo ""
echo "=== 7. Starting Our Bot ==="
cd /var/www/smartcity-frontend

# Clear log
> /tmp/telegram_bot.log

# Start with backend venv
/var/www/smartcity-backend/venv/bin/python3 bot.py > /tmp/telegram_bot.log 2>&1 &
BOT_PID=$!

echo "  ✅ Bot started: PID $BOT_PID"

# Wait for bot to initialize
sleep 10

# 8. Verify
echo ""
echo "=== 8. Final Verification ==="

# Count running bots
BOT_COUNT=$(ps aux | grep "bot.py" | grep -v grep | wc -l)
echo "  Running bots: $BOT_COUNT"

if [ "$BOT_COUNT" -eq 1 ]; then
    echo "  ✅ SUCCESS! Only 1 bot running"
elif [ "$BOT_COUNT" -eq 0 ]; then
    echo "  ❌ ERROR! No bot running"
    echo "  Check logs:"
    tail -20 /tmp/telegram_bot.log
    exit 1
else
    echo "  ❌ ERROR! Multiple bots running:"
    ps aux | grep "bot.py" | grep -v grep
    exit 1
fi

# Check for conflicts
echo ""
echo "=== 9. Conflict Check ==="
sleep 5
if tail -20 /tmp/telegram_bot.log | grep -i "409\|conflict"; then
    echo "  ❌ Bot still has conflicts!"
    echo "  Wait another minute and check again"
else
    echo "  ✅ No conflicts detected!"
fi

# Show bot logs
echo ""
echo "=== 10. Bot Logs ==="
tail -20 /tmp/telegram_bot.log

echo ""
echo "=========================================="
echo "✅ CLEANUP COMPLETE!"
echo "=========================================="
echo ""
echo "Bot Status:"
ps aux | grep "bot.py" | grep -v grep
echo ""
echo "Monitor bot: tail -f /tmp/telegram_bot.log"
echo "Test: Scan QR code from phone"
echo ""
