from django.core.management.base import BaseCommand
from django.utils import timezone
from smartcity_app.models import WasteBin
import random
import requests
from datetime import datetime, timedelta
import base64
import io
from PIL import Image


class Command(BaseCommand):
    help = 'Simulate camera screenshots every 30 minutes with enhanced AI analysis'

    def add_arguments(self, parser):
        parser.add_argument(
            '--run-once',
            action='store_true',
            help='Run the simulation once instead of continuously',
        )

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('Starting camera screenshot simulation...')
        )
        
        if options['run_once']:
            self.simulate_screenshots()
        else:
            self.run_continuous_simulation()
        
        self.stdout.write(
            self.style.SUCCESS('Camera screenshot simulation completed')
        )

    def run_continuous_simulation(self):
        """Run the simulation continuously every 30 minutes"""
        import time
        
        while True:
            self.simulate_screenshots()
            self.stdout.write(
                self.style.SUCCESS(f'Waiting 30 minutes for next screenshot cycle at {timezone.now() + timedelta(minutes=30)}')
            )
            time.sleep(30 * 60)  # Wait 30 minutes

    def simulate_screenshots(self):
        """Capture REAL camera screenshots for all waste bins with REAL AI analysis - NO simulation"""
        bins = WasteBin.objects.all()
        
        for bin in bins:
            # CRITICAL: Only process bins with REAL camera URLs
            if not bin.camera_url:
                self.stdout.write(f"⚠️ Bin {bin.id} ({bin.address}) has no camera_url - skipping")
                continue
            
            # CRITICAL: Skip placeholder URLs
            if 'placeholder' in bin.camera_url.lower() or 'via.placeholder' in bin.camera_url.lower():
                self.stdout.write(f"⚠️ Bin {bin.id} ({bin.address}) has placeholder camera URL - skipping")
                continue
            
            try:
                # Download REAL image from camera URL
                import requests as req
                import base64
                from io import BytesIO
                from smartcity_app.views import analyze_bin_image_backend
                
                response = req.get(bin.camera_url, timeout=10)
                if response.status_code == 200:
                    # Convert image to base64 for REAL AI analysis
                    image_bytes = BytesIO(response.content).read()
                    image_base64 = base64.b64encode(image_bytes).decode('utf-8')
                    
                    # Call REAL AI analysis (no simulation)
                    ai_analysis = analyze_bin_image_backend(image_base64)
                    
                    # Update bin status based on REAL AI analysis
                    bin.image_url = bin.camera_url  # Use real camera URL
                    bin.image_source = 'CCTV'
                    bin.last_analysis = f"AI tahlili (CCTV): {ai_analysis.get('notes', 'Tahlil amalga oshirildi')}, IsFull: {ai_analysis.get('isFull')}, FillLevel: {ai_analysis.get('fillLevel')}%, Conf: {ai_analysis.get('confidence')}%"
                    bin.fill_level = ai_analysis.get('fillLevel', bin.fill_level)
                    bin.is_full = ai_analysis.get('isFull', bin.is_full)
                    
                    bin.save()
                    
                    self.stdout.write(
                        f"✅ Bin {bin.id} ({bin.address}) analyzed with REAL camera image: fill level {bin.fill_level}%, "
                        f"full status: {bin.is_full}, confidence: {ai_analysis.get('confidence')}%"
                    )
                else:
                    self.stdout.write(
                        f"❌ Bin {bin.id} ({bin.address}) camera URL returned {response.status_code} - cannot capture screenshot"
                    )
            except Exception as e:
                self.stdout.write(
                    f"❌ Error capturing screenshot for bin {bin.id} ({bin.address}): {str(e)}"
                )

    # REMOVED: generate_simulated_image - we only use REAL camera URLs
    # REMOVED: analyze_image_with_ai - we use analyze_bin_image_backend from views.py for REAL AI analysis