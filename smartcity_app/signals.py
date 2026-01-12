"""
Django signals for automatic operations on model save
"""
import os
import qrcode
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings
from .models import WasteBin


@receiver(post_save, sender=WasteBin)
def generate_qr_code_on_create(sender, instance, created, **kwargs):
    """
    Automatically generate QR code when a new WasteBin is created
    """
    if created and not instance.qr_code_url:
        # Create QR codes directory if it doesn't exist
        qr_codes_dir = os.path.join(settings.MEDIA_ROOT, 'qr_codes')
        os.makedirs(qr_codes_dir, exist_ok=True)
        
        # Create QR code with bin ID for Telegram bot
        qr_data = f"https://t.me/tozafargonabot?start={instance.id}"
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(qr_data)
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white")
        
        # Save the QR code image
        qr_filename = f"bin_{instance.id}_qr.png"
        qr_path = os.path.join(qr_codes_dir, qr_filename)
        
        img.save(qr_path)
        
        # Update the bin's QR code URL field (use production URL)
        qr_url = f"https://ferganaapi.cdcgroup.uz/media/qr_codes/{qr_filename}"
        
        # Update the bin object with the QR code URL (use update to avoid infinite loop)
        WasteBin.objects.filter(pk=instance.pk).update(qr_code_url=qr_url)
        
        print(f'✅ QR code auto-generated for waste bin {instance.id}')
        print(f'   QR URL: {qr_url}')
