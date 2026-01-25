from django.core.management.base import BaseCommand
from django.utils import timezone
from smartcity_app.models import WasteBin
import random
import time
from datetime import datetime, timedelta


class Command(BaseCommand):
    help = 'Automatically analyze waste bins via camera every 30 minutes'

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('Starting automatic waste bin analysis...')
        )
        
        # For demo purposes, we'll just update the bins once
        # In a real system, this would run continuously or be scheduled with cron
        self.analyze_bins()
        
        self.stdout.write(
            self.style.SUCCESS('Waste bin analysis completed')
        )
    
    def analyze_bins(self):
        """Analyze all waste bins using REAL camera images only - NO random generation"""
        bins = WasteBin.objects.all()
        
        for bin in bins:
            # CRITICAL: Only analyze if there's a REAL camera URL
            if not bin.camera_url:
                self.stdout.write(f"⚠️ Bin {bin.id} ({bin.address}) has no camera_url - skipping analysis")
                continue
            
            # CRITICAL: Only analyze if camera URL is valid (not placeholder)
            if 'placeholder' in bin.camera_url.lower() or 'via.placeholder' in bin.camera_url.lower():
                self.stdout.write(f"⚠️ Bin {bin.id} ({bin.address}) has placeholder image URL - skipping analysis")
                continue
            
            old_fill_level = bin.fill_level
            old_is_full = bin.is_full
            
            # Try to download and analyze the REAL image from camera_url
            try:
                import requests as req
                import base64
                from io import BytesIO
                from smartcity_app.views import analyze_bin_image_backend
                
                # Download image from camera URL
                response = req.get(bin.camera_url, timeout=10)
                if response.status_code == 200:
                    # Convert image to base64 for AI analysis
                    image_bytes = BytesIO(response.content).read()
                    image_base64 = base64.b64encode(image_bytes).decode('utf-8')
                    
                    # Call REAL AI analysis (no simulation)
                    ai_result = analyze_bin_image_backend(image_base64)
                    
                    # Update bin status based on REAL AI analysis
                    bin.fill_level = ai_result['fillLevel']
                    bin.is_full = ai_result['isFull']
                    bin.last_analysis = f"AI tahlili (CCTV): {ai_result['notes']}, IsFull: {ai_result['isFull']}, FillLevel: {ai_result['fillLevel']}%, Conf: {ai_result['confidence']}%"
                    bin.image_source = 'CCTV'
                    bin.image_url = bin.camera_url  # Save the camera image URL
                    
                    bin.save()
                    
                    # Log the change
                    if old_fill_level != bin.fill_level or old_is_full != bin.is_full:
                        self.stdout.write(
                            f"✅ Bin {bin.id} ({bin.address}) analyzed: fill level {old_fill_level}% -> {bin.fill_level}%, "
                            f"full status: {old_is_full} -> {bin.is_full} (AI confidence: {ai_result['confidence']}%)"
                        )
                    else:
                        self.stdout.write(
                            f"ℹ️ Bin {bin.id} ({bin.address}) analyzed: no change (fill level: {bin.fill_level}%, AI confidence: {ai_result['confidence']}%)"
                        )
                else:
                    self.stdout.write(
                        f"❌ Bin {bin.id} ({bin.address}) camera URL returned {response.status_code} - cannot analyze"
                    )
            except Exception as e:
                self.stdout.write(
                    f"❌ Error analyzing bin {bin.id} ({bin.address}): {str(e)}"
                )
                # Don't update bin if analysis fails - keep existing values