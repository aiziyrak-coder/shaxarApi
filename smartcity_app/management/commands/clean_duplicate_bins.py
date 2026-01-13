#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Takrorlanuvchi Waste Bin'larni Tozalash
"""
from django.core.management.base import BaseCommand
from smartcity_app.models import WasteBin, Organization
from collections import defaultdict
from django.db.models import Count


class Command(BaseCommand):
    help = 'Takrorlanuvchi waste bin\'larni topadi va tozalaydi'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Faqat ko\'rsatadi, o\'chirmaydi',
        )
        parser.add_argument(
            '--keep-latest',
            type=int,
            default=18,
            help='Nechta eng so\'nggi bin\'ni saqlash (default: 18)',
        )
        parser.add_argument(
            '--by-address',
            action='store_true',
            help='Address bo\'yicha takrorlanuvchilarni topish',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        keep_latest = options['keep_latest']
        by_address = options['by_address']

        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write(self.style.SUCCESS('Takrorlanuvchi Waste Bin\'larni Tozalash'))
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write('')

        # Fergana organization'ni topish
        try:
            fergana_org = Organization.objects.get(name='Fergana')
        except Organization.DoesNotExist:
            self.stdout.write(self.style.ERROR('❌ Fergana organization topilmadi!'))
            return

        # Barcha waste bin'larni olish
        all_bins = WasteBin.objects.filter(organization=fergana_org).select_related('location')
        total_count = all_bins.count()

        self.stdout.write(f'📊 Jami waste bin\'lar: {total_count}')
        self.stdout.write(f'🎯 Saqlash kerak: {keep_latest} ta')
        self.stdout.write('')

        if total_count <= keep_latest:
            self.stdout.write(self.style.SUCCESS(f'✅ Barcha bin\'lar ({total_count}) saqlash kerak miqdordan kam!'))
            return

        # Takrorlanuvchi bin'larni topish
        if by_address:
            # Address bo'yicha takrorlanuvchilar
            address_groups = defaultdict(list)
            for bin in all_bins:
                address_groups[bin.address].append(bin)
            
            duplicates = {addr: bins for addr, bins in address_groups.items() if len(bins) > 1}
        else:
            # Location (koordinata) bo'yicha takrorlanuvchilar
            location_groups = defaultdict(list)
            for bin in all_bins:
                key = (bin.location.lat, bin.location.lng)
                location_groups[key].append(bin)
            
            duplicates = {loc: bins for loc, bins in location_groups.items() if len(bins) > 1}

        # Eng so'nggi bin'larni saqlash (created_at yoki id bo'yicha)
        # Agar created_at bo'lmasa, id bo'yicha tartiblash
        all_bins_sorted = sorted(all_bins, key=lambda b: b.id, reverse=True)
        bins_to_keep = all_bins_sorted[:keep_latest]
        bins_to_delete = all_bins_sorted[keep_latest:]

        self.stdout.write(self.style.WARNING('=' * 60))
        self.stdout.write(self.style.WARNING('O\'CHIRILADIGAN BIN\'LAR:'))
        self.stdout.write(self.style.WARNING('=' * 60))
        
        for i, bin in enumerate(bins_to_delete, 1):
            self.stdout.write(f'{i}. ID: {bin.id}')
            self.stdout.write(f'   Address: {bin.address}')
            self.stdout.write(f'   Location: ({bin.location.lat}, {bin.location.lng})')
            self.stdout.write(f'   Fill Level: {bin.fill_level}%')
            self.stdout.write('')

        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write(self.style.SUCCESS('SAQLANADIGAN BIN\'LAR:'))
        self.stdout.write(self.style.SUCCESS('=' * 60))
        
        for i, bin in enumerate(bins_to_keep, 1):
            self.stdout.write(f'{i}. ID: {bin.id}')
            self.stdout.write(f'   Address: {bin.address}')
            self.stdout.write(f'   Location: ({bin.location.lat}, {bin.location.lng})')
            self.stdout.write(f'   Fill Level: {bin.fill_level}%')
            self.stdout.write('')

        if dry_run:
            self.stdout.write(self.style.WARNING('=' * 60))
            self.stdout.write(self.style.WARNING('⚠️  DRY RUN - Hech narsa o\'chirilmadi!'))
            self.stdout.write(self.style.WARNING('O\'chirish uchun --dry-run flag\'ini olib tashlang'))
            self.stdout.write(self.style.WARNING('=' * 60))
            return

        # Tasdiqlash
        self.stdout.write(self.style.ERROR('=' * 60))
        self.stdout.write(self.style.ERROR(f'⚠️  {len(bins_to_delete)} ta bin o\'chiriladi!'))
        self.stdout.write(self.style.ERROR('=' * 60))
        
        confirm = input('Davom etishni tasdiqlaysizmi? (yes/no): ')
        if confirm.lower() != 'yes':
            self.stdout.write(self.style.WARNING('❌ Bekor qilindi!'))
            return

        # O'chirish
        deleted_count = 0
        for bin in bins_to_delete:
            try:
                # Location'ni ham o'chirish (OneToOneField)
                location = bin.location
                bin.delete()
                location.delete()
                deleted_count += 1
                self.stdout.write(f'✅ O\'chirildi: {bin.address}')
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'❌ Xatolik ({bin.address}): {e}'))

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write(self.style.SUCCESS(f'✅ Muvaffaqiyatli! {deleted_count} ta bin o\'chirildi'))
        self.stdout.write(self.style.SUCCESS(f'📊 Qolgan bin\'lar: {WasteBin.objects.filter(organization=fergana_org).count()} ta'))
        self.stdout.write(self.style.SUCCESS('=' * 60))
