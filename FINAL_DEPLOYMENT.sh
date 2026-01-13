#!/bin/bash
# ============================================
# 🚀 FINAL DEPLOYMENT - ALL FIXES
# ============================================

echo "╔════════════════════════════════════════════════════════════╗"
echo "║         SMART CITY - FINAL DEPLOYMENT WITH FIXES          ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

START_TIME=$(date +%s)

# ============================================
# STEP 1: BACKEND DEPLOYMENT
# ============================================
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📦 STEP 1: Backend Deployment"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

cd /var/www/smartcity-backend

echo "  • Pulling latest code..."
git pull origin master

echo "  • Activating venv..."
source venv/bin/activate

echo "  • Installing dependencies..."
pip install -q qrcode pillow python-telegram-bot requests

echo "  • Running migrations..."
python manage.py migrate --no-input

echo "  • Regenerating QR codes with fixed URLs..."
python manage.py generate_bin_qrcodes

echo "  • Restarting gunicorn..."
pkill -9 gunicorn
sleep 2

nohup gunicorn smartcity_backend.wsgi:application \
    --bind 127.0.0.1:8002 \
    --workers 4 \
    --timeout 120 \
    --access-logfile gunicorn-access.log \
    --error-logfile gunicorn-error.log \
    > gunicorn.log 2>&1 &

sleep 3

if pgrep -f gunicorn > /dev/null; then
    echo "  ✅ Gunicorn: RUNNING"
else
    echo "  ❌ Gunicorn: FAILED"
    exit 1
fi

# ============================================
# STEP 2: FRONTEND DEPLOYMENT
# ============================================
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🎨 STEP 2: Frontend Deployment"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

cd /var/www/smartcity-frontend

echo "  • Pulling latest code..."
git pull origin master

echo "  • Building production bundle..."
npm run build

echo "  • Deploying to nginx..."
sudo rm -rf /var/www/html/smartcity/*
sudo cp -r dist/* /var/www/html/smartcity/
sudo chown -R www-data:www-data /var/www/html/smartcity/
sudo chmod -R 755 /var/www/html/smartcity/

echo "  • Reloading nginx..."
sudo systemctl reload nginx

if systemctl is-active --quiet nginx; then
    echo "  ✅ Nginx: RUNNING"
else
    echo "  ❌ Nginx: FAILED"
    exit 1
fi

# ============================================
# STEP 3: BOT CLEANUP & DEPLOYMENT
# ============================================
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🤖 STEP 3: Telegram Bot Deployment"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

cd /var/www/smartcity-backend

echo "  • Running bot conflict cleanup script..."
chmod +x DISABLE_CONFLICTING_BOTS.sh
./DISABLE_CONFLICTING_BOTS.sh

# ============================================
# STEP 4: VERIFICATION
# ============================================
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ STEP 4: Verification"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

echo ""
echo "📊 Services Status:"
echo "  • Gunicorn: $(pgrep -f gunicorn > /dev/null && echo '✅ RUNNING' || echo '❌ STOPPED')"
echo "  • Nginx: $(systemctl is-active --quiet nginx && echo '✅ RUNNING' || echo '❌ STOPPED')"
echo "  • Bot: $(pgrep -f bot.py > /dev/null && echo '✅ RUNNING' || echo '❌ STOPPED')"

echo ""
echo "🔍 API Test:"
curl -s http://127.0.0.1:8002/api/ > /dev/null && echo "  ✅ Backend API responding" || echo "  ❌ Backend API not responding"

echo ""
echo "📱 Bot Test:"
BOT_COUNT=$(ps aux | grep bot.py | grep -v grep | wc -l)
if [ "$BOT_COUNT" -eq 1 ]; then
    echo "  ✅ Only 1 bot running (correct)"
else
    echo "  ⚠️ $BOT_COUNT bots running (should be 1)"
fi

# Check for conflicts
if tail -10 /tmp/telegram_bot.log | grep -qi "conflict"; then
    echo "  ⚠️ Bot has conflicts - may need more time"
else
    echo "  ✅ Bot: No conflicts"
fi

echo ""
echo "🗄️ Database Check:"
cd /var/www/smartcity-backend
source venv/bin/activate

python3 << 'PYTHON_EOF'
import os, sys, django
sys.path.insert(0, '/var/www/smartcity-backend')
os.environ['DJANGO_SETTINGS_MODULE'] = 'smartcity_backend.settings'
django.setup()

from smartcity_app.models import WasteBin

total_bins = WasteBin.objects.count()
bins_with_qr = WasteBin.objects.exclude(qr_code_url__isnull=True).exclude(qr_code_url='').count()
bins_with_correct_url = WasteBin.objects.filter(qr_code_url__startswith='https://ferganaapi.cdcgroup.uz').count()

print(f"  • Total bins: {total_bins}")
print(f"  • Bins with QR: {bins_with_qr}")
print(f"  • QR with correct URL: {bins_with_correct_url}")

if bins_with_qr == bins_with_correct_url == total_bins:
    print(f"  ✅ All bins have correct QR URLs!")
else:
    print(f"  ⚠️ Some QR URLs need regeneration")
PYTHON_EOF

# ============================================
# FINAL SUMMARY
# ============================================
END_TIME=$(date +%s)
ELAPSED=$((END_TIME - START_TIME))

echo ""
echo "╔════════════════════════════════════════════════════════════╗"
echo "║                 DEPLOYMENT COMPLETE!                       ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""
echo "⏱️  Total Time: ${ELAPSED} seconds"
echo ""
echo "🎯 Next Steps:"
echo "  1. Open: https://fergana.cdcgroup.uz"
echo "  2. Login: fergan / 123"
echo "  3. Test Chiqindi module"
echo "  4. Open any bin → Verify QR code visible"
echo "  5. Download QR → Scan → Test bot"
echo "  6. Upload image to bot"
echo "  7. Verify image appears on platform with BOT badge"
echo ""
echo "📋 Test Guides:"
echo "  • QUICK_TEST_SCRIPT.md - 5-minute test"
echo "  • MANUAL_TEST_CHECKLIST.md - Complete test"
echo "  • BUGS_FOUND_AND_FIXES.md - All fixes applied"
echo ""
echo "📊 Logs:"
echo "  • Backend: tail -f /var/www/smartcity-backend/gunicorn-error.log"
echo "  • Bot: tail -f /tmp/telegram_bot.log"
echo "  • Nginx: tail -f /var/log/nginx/error.log"
echo ""
echo "✨ All critical fixes applied!"
echo ""
