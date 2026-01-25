from django.core.management.base import BaseCommand
from django.utils import timezone
from smartcity_app.models import IoTDevice, Room, Boiler
import random
import requests
import time
from datetime import datetime
import json


class Command(BaseCommand):
    help = '⚠️ DEPRECATED: This command generates FAKE data. Use real IoT devices instead!'
    
    def handle(self, *args, **options):
        self.stdout.write(
            self.style.ERROR('=' * 60)
        )
        self.stdout.write(
            self.style.ERROR('⚠️  UYAT: Bu command FAKE ma\'lumotlar generatsiya qiladi!')
        )
        self.stdout.write(
            self.style.ERROR('=' * 60)
        )
        self.stdout.write('')
        self.stdout.write(
            self.style.WARNING('Bu command o\'chirilgan yoki o\'zgartirilgan.')
        )
        self.stdout.write('')
        self.stdout.write(
            self.style.SUCCESS('Real IoT sensor ma\'lumotlari faqat quyidagilar orqali keladi:')
        )
        self.stdout.write('  1. Real ESP32/ESP8266 qurilmalaridan Telegram bot orqali')
        self.stdout.write('  2. IoT bot (iot_monitor.py) Telegram kanaldan real ma\'lumotlarni o\'qib yuboradi')
        self.stdout.write('  3. API endpoint: /api/iot-devices/data/update/ - real qurilmalardan to\'g\'ridan-to\'g\'ri')
        self.stdout.write('')
        self.stdout.write(
            self.style.ERROR('Iltimos, faqat real sensor ma\'lumotlaridan foydalaning!')
        )