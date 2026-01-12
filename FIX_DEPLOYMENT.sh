#!/bin/bash
# Fix Deployment Issues

echo "=========================================="
echo "🔧 FIXING DEPLOYMENT ISSUES"
echo "=========================================="

# ============================================
# 1️⃣ FIX GUNICORN - Find actual service name
# ============================================
echo ""
echo "1️⃣ Finding Gunicorn service..."

# Check if gunicorn is running
if pgrep -f gunicorn > /dev/null; then
    echo "✅ Gunicorn is running"
    
    # Find the process and restart it
    echo "Killing old gunicorn processes..."
    pkill -9 gunicorn
    
    # Start gunicorn manually
    echo "Starting gunicorn manually..."
    cd /var/www/smartcity-backend
    source venv/bin/activate
    
    # Start gunicorn in background
    nohup gunicorn smartcity_backend.wsgi:application \
        --bind 127.0.0.1:8002 \
        --workers 4 \
        --timeout 120 \
        --access-logfile /var/www/smartcity-backend/gunicorn-access.log \
        --error-logfile /var/www/smartcity-backend/gunicorn-error.log \
        > /var/www/smartcity-backend/gunicorn.log 2>&1 &
    
    echo "✅ Gunicorn started manually"
    sleep 2
    
    # Verify gunicorn is running
    if pgrep -f gunicorn > /dev/null; then
        echo "✅ Gunicorn is running: PID $(pgrep -f gunicorn)"
    else
        echo "❌ Failed to start gunicorn"
    fi
else
    echo "⚠️ Gunicorn was not running, starting now..."
    
    cd /var/www/smartcity-backend
    source venv/bin/activate
    
    nohup gunicorn smartcity_backend.wsgi:application \
        --bind 127.0.0.1:8002 \
        --workers 4 \
        --timeout 120 \
        --access-logfile /var/www/smartcity-backend/gunicorn-access.log \
        --error-logfile /var/www/smartcity-backend/gunicorn-error.log \
        > /var/www/smartcity-backend/gunicorn.log 2>&1 &
    
    sleep 2
    
    if pgrep -f gunicorn > /dev/null; then
        echo "✅ Gunicorn started: PID $(pgrep -f gunicorn)"
    else
        echo "❌ Failed to start gunicorn"
        echo "Check logs: tail -50 /var/www/smartcity-backend/gunicorn-error.log"
    fi
fi

# ============================================
# 2️⃣ FIX TELEGRAM BOT - Library version issue
# ============================================
echo ""
echo "2️⃣ Fixing Telegram Bot library..."

cd /var/www/smartcity-frontend

# Check current python-telegram-bot version
echo "Current python-telegram-bot version:"
python3 -c "import telegram; print(telegram.__version__)" 2>/dev/null || echo "Not installed"

# The error suggests slots=True issue - update to latest version
echo "Updating python-telegram-bot to latest version..."
pip3 install --upgrade python-telegram-bot

echo "New version:"
python3 -c "import telegram; print(telegram.__version__)" 2>/dev/null || echo "Failed to install"

# Kill old bot processes
echo "Stopping old bot processes..."
pkill -9 -f "bot.py" || echo "No bot running"

# Start bot
echo "Starting bot..."
nohup python3 bot.py > /tmp/telegram_bot.log 2>&1 &
BOT_PID=$!
echo "Bot PID: $BOT_PID"

# Wait and check logs
sleep 3

if pgrep -f "bot.py" > /dev/null; then
    echo "✅ Bot is running: PID $(pgrep -f 'bot.py')"
else
    echo "❌ Bot failed to start"
    echo "Checking logs:"
    tail -30 /tmp/telegram_bot.log
fi

# ============================================
# 3️⃣ TEST BACKEND API
# ============================================
echo ""
echo "3️⃣ Testing Backend API..."

# Test API health
RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8002/api/)

if [ "$RESPONSE" = "200" ]; then
    echo "✅ Backend API is working (HTTP 200)"
elif [ "$RESPONSE" = "301" ] || [ "$RESPONSE" = "302" ]; then
    echo "✅ Backend API is redirecting (HTTP $RESPONSE)"
else
    echo "❌ Backend API not responding (HTTP $RESPONSE)"
    echo "Check gunicorn logs:"
    tail -20 /var/www/smartcity-backend/gunicorn-error.log
fi

# ============================================
# 4️⃣ CREATE TEST QR CODE
# ============================================
echo ""
echo "4️⃣ Testing QR Code Auto-Generation..."

cd /var/www/smartcity-backend
source venv/bin/activate

python3 << 'PYTHON_EOF'
import os
import sys
import django

# Setup Django
sys.path.insert(0, '/var/www/smartcity-backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smartcity_backend.settings')
django.setup()

from smartcity_app.models import WasteBin, Organization, Coordinate

# Get first organization
org = Organization.objects.first()
if not org:
    print("❌ No organization found! Create one first.")
    sys.exit(1)

# Create test bin
coord = Coordinate.objects.create(lat=40.3833, lng=71.7833)
bin = WasteBin.objects.create(
    organization=org,
    address="🧪 TEST BIN - QR Code Auto-Generation",
    location=coord,
    toza_hudud="1-sonli Toza Hudud",
    fill_level=0,
    is_full=False
)

print(f"✅ Test bin created: {bin.id}")
print(f"✅ Address: {bin.address}")
print(f"✅ QR URL: {bin.qr_code_url or '❌ Not generated'}")

# Check if QR code was auto-generated
if bin.qr_code_url:
    print("")
    print("🎉 AUTO QR CODE GENERATION WORKS!")
    print(f"📱 Scan this QR: {bin.qr_code_url}")
else:
    print("")
    print("⚠️ QR code was not auto-generated")
    print("Signal might not be working. Check smartcity_app/apps.py")
PYTHON_EOF

# ============================================
# 5️⃣ FINAL STATUS
# ============================================
echo ""
echo "=========================================="
echo "📊 FINAL STATUS"
echo "=========================================="
echo ""

# Gunicorn
if pgrep -f gunicorn > /dev/null; then
    echo "✅ Gunicorn: RUNNING (PID $(pgrep -f gunicorn | head -1))"
else
    echo "❌ Gunicorn: NOT RUNNING"
fi

# Bot
if pgrep -f "bot.py" > /dev/null; then
    echo "✅ Bot: RUNNING (PID $(pgrep -f 'bot.py'))"
else
    echo "❌ Bot: NOT RUNNING"
fi

# Nginx
if systemctl is-active --quiet nginx; then
    echo "✅ Nginx: RUNNING"
else
    echo "❌ Nginx: NOT RUNNING"
fi

echo ""
echo "=========================================="
echo "📋 LOGS"
echo "=========================================="
echo ""
echo "Gunicorn: tail -f /var/www/smartcity-backend/gunicorn-error.log"
echo "Bot:      tail -f /tmp/telegram_bot.log"
echo "Nginx:    tail -f /var/log/nginx/error.log"
echo ""
echo "=========================================="
echo "🧪 TEST QR CODE"
echo "=========================================="
echo ""
echo "1. Go to: https://fergana.cdcgroup.uz"
echo "2. Login: fergan / 123"
echo "3. Open 'Chiqindi' module"
echo "4. Find '🧪 TEST BIN' in the list"
echo "5. Click on it to see QR code"
echo "6. Scan QR with phone → Bot opens"
echo "7. Send image to bot"
echo "8. Check platform for bot image!"
echo ""
