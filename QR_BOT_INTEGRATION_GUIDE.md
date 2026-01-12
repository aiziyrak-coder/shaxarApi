# 📱 QR Code + Telegram Bot Integration Guide

## ✅ Tayyor Funksiyalar

### 1️⃣ Avtomatik QR Code Yaratish
**Yangi WasteBin yaratilganda avtomatik QR code yaratiladi!**

```python
# Backend: smartcity_app/signals.py
@receiver(post_save, sender=WasteBin)
def generate_qr_code_on_create(sender, instance, created, **kwargs):
    """
    Automatically generate QR code when a new WasteBin is created
    """
    if created and not instance.qr_code_url:
        # QR code avtomatik yaratiladi
        qr_data = f"https://t.me/tozafargonabot?start={instance.id}"
        # ...yaratish logikasi...
```

### 2️⃣ QR Code Scan → Bot'ga Kirish
QR code scan qilinganda Telegram bot'ga o'tadi:

```
QR Code: https://t.me/tozafargonabot?start={bin_id}
         ↓
Telegram Bot: /start {bin_id}
         ↓
Bot: Konteyner ma'lumotlarini ko'rsatadi
```

### 3️⃣ Rasm Yuklash va Platform'da Ko'rinish
Bot orqali yuklangan rasm **avtomatik** platform'da ko'rinadi:

- Bot rasm qabul qiladi
- AI tahlil qiladi (Gemini API)
- Backend'ga yuboradi
- Platform'da real-time ko'rinadi
- **BOT** badge bilan ko'rsatiladi (CCTV dan farqlash uchun)

---

## 🚀 Deployment

### Backend (Django)

```bash
# 1. SSH into server
ssh root@167.71.53.238

# 2. Navigate to backend
cd /var/www/smartcity-backend

# 3. Pull latest code
git pull origin master

# 4. Install new dependencies (if any)
source venv/bin/activate
pip install qrcode pillow

# 5. Run migrations (if needed)
python manage.py migrate

# 6. Generate QR codes for existing bins
python manage.py generate_bin_qrcodes

# 7. Restart gunicorn
sudo systemctl restart gunicorn

# 8. Check status
sudo systemctl status gunicorn
```

### Frontend (React)

```bash
# 1. Navigate to frontend
cd /var/www/smartcity-frontend

# 2. Pull latest code
git pull origin master

# 3. Build
npm run build

# 4. Deploy to nginx
sudo rm -rf /var/www/html/smartcity/*
sudo cp -r dist/* /var/www/html/smartcity/

# 5. Reload nginx
sudo systemctl reload nginx
```

### Telegram Bot

```bash
# 1. Stop existing bot
pkill -f "bot.py" || echo "No bot running"

# 2. Navigate to frontend (bot.py is there)
cd /var/www/smartcity-frontend

# 3. Start bot in background
nohup python3 bot.py > /tmp/telegram_bot.log 2>&1 &

# 4. Check logs
tail -f /tmp/telegram_bot.log
```

---

## 🧪 Test Qilish

### 1. Backend Test

```bash
# QR code yaratilishini test
curl -X POST https://ferganaapi.cdcgroup.uz/api/waste-bins/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Token YOUR_TOKEN" \
  -d '{
    "address": "Test manzil",
    "location": {"lat": 40.3833, "lng": 71.7833},
    "toza_hudud": "1-sonli Toza Hudud"
  }'

# Response'da qr_code_url borligini tekshiring
```

### 2. QR Code Scan Test

1. Backend'dan QR code URL'ni oling:
   ```bash
   https://ferganaapi.cdcgroup.uz/media/qr_codes/bin_{id}_qr.png
   ```

2. QR kodni telefondan skaner qiling (Telegram yoki QR scanner app)

3. Bot `/start {bin_id}` bilan ochilishini tekshiring

4. Konteyner ma'lumotlari ko'rinishini tekshiring

### 3. Rasm Yuklash Test

1. QR scan qiling → bot'ga kiring
2. Konteyner rasmini bot'ga yuboring
3. Bot AI tahlil qilishini kuting (5-10 sekund)
4. Bot javob berishi kerak:
   ```
   ✅ Rasm qabul qilindi va tahlil qilindi!
   📦 Konteyner: ...
   🚦 Yangi status: To'la / Bo'sh
   📊 To'ldirish darajasi: 85%
   🔍 AI ishonchlilik: 92%
   ```

5. Platform'da tekshiring:
   - **Chiqindi** moduliga o'ting
   - Konteynerni tanlang
   - Rasm ko'rinishi kerak
   - **"TELEGRAM BOT"** badge bilan

---

## 📋 Fayllar Ro'yxati

### Backend
```
backend/
├── smartcity_app/
│   ├── signals.py                    # ✅ YANGI - Avtomatik QR code
│   ├── apps.py                       # ✅ YANGILANDI - Signal import
│   ├── models.py                     # ✅ WasteBin.qr_code_url, .image
│   ├── management/commands/
│   │   └── generate_bin_qrcodes.py  # ✅ YANGILANDI - Production URL
```

### Frontend
```
frontend/
├── bot.py                            # ✅ YANGILANDI - API URL
├── iot_monitor.py                    # ✅ YANGILANDI - API URL
├── components/
│   └── WasteManagement.tsx           # ✅ YANGILANDI - Image URL, QR display
```

---

## 🔧 Troubleshooting

### QR Code yaratilmayapti?

```bash
# 1. qrcode kutubxonasi o'rnatilganligini tekshiring
pip show qrcode

# 2. Agar yo'q bo'lsa, o'rnating
pip install qrcode[pil]

# 3. Signal ishlayotganligini tekshiring
python manage.py shell
>>> from smartcity_app.models import WasteBin
>>> from smartcity_app.signals import generate_qr_code_on_create
>>> print("Signal imported successfully")
```

### Bot rasm qabul qilmayapti?

```bash
# 1. Bot ishlab turganligini tekshiring
ps aux | grep bot.py

# 2. Bot loglarini ko'ring
tail -100 /tmp/telegram_bot.log

# 3. API token to'g'riligini tekshiring
grep BOT_TOKEN /var/www/smartcity-frontend/bot.py
```

### Platform'da rasm ko'rinmayapti?

1. **Backend'da rasm bor**ligini tekshiring:
   ```bash
   curl https://ferganaapi.cdcgroup.uz/api/waste-bins/{bin_id}/ | jq '.image'
   ```

2. **CORS sozlamalari** to'g'riligini tekshiring:
   ```python
   # backend/smartcity_backend/settings.py
   CORS_ALLOWED_ORIGINS = [
       "https://fergana.cdcgroup.uz",
       "https://ferganaapi.cdcgroup.uz",
   ]
   ```

3. **Media files** sozlamalari:
   ```python
   # settings.py
   MEDIA_URL = '/media/'
   MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
   ```

4. **Nginx** media files uchun to'g'ri sozlanganligini tekshiring:
   ```nginx
   location /media/ {
       alias /var/www/smartcity-backend/media/;
   }
   ```

---

## 📊 Texnik Ma'lumotlar

### QR Code Format
- **URL**: `https://t.me/tozafargonabot?start={bin_id}`
- **Size**: 300x300 pixels
- **Format**: PNG
- **Error Correction**: LOW (L)

### Image Upload
- **Max Size**: 20 MB (Telegram limit)
- **Format**: JPEG/PNG
- **AI Analysis**: Google Gemini Pro Vision
- **Processing Time**: 5-10 seconds

### API Endpoints
- `POST /api/waste-bins/` - Create bin (auto QR code)
- `PATCH /api/waste-bins/{id}/` - Update bin
- `PATCH /api/waste-bins/{id}/update-image-file/` - Upload image

---

## ✅ Final Checklist

- [ ] Backend deployed with signals
- [ ] QR codes generated for all bins
- [ ] Bot running in background
- [ ] Frontend built and deployed
- [ ] Test QR scan → bot opens
- [ ] Test image upload → platform updates
- [ ] Test real-time image display
- [ ] BOT badge visible on platform

---

**Last Updated**: January 13, 2026  
**Developer**: CDCGroup / CraDev  
**Status**: ✅ Production Ready
