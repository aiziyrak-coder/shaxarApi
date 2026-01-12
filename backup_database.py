#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Database Backup Script
Ma'lumotlarni saqlab qolish uchun
"""
import os
import shutil
from datetime import datetime

def backup_database():
    """Create a backup of the database"""
    # Database fayl yo'li
    db_file = 'db.sqlite3'
    
    if not os.path.exists(db_file):
        print("[ERROR] Database fayl topilmadi!")
        return False
    
    # Backup papkasini yaratish
    backup_dir = 'backups'
    if not os.path.exists(backup_dir):
        os.makedirs(backup_dir)
    
    # Backup fayl nomi (timestamp bilan)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_file = os.path.join(backup_dir, f'db_backup_{timestamp}.sqlite3')
    
    # Backup yaratish
    try:
        shutil.copy2(db_file, backup_file)
        file_size = os.path.getsize(backup_file) / 1024  # KB
        print("[SUCCESS] Database backup yaratildi!")
        print(f"[FILE] {backup_file}")
        print(f"[SIZE] {file_size:.2f} KB")
        return True
    except Exception as e:
        print(f"[ERROR] Backup yaratishda xato: {e}")
        return False

if __name__ == '__main__':
    print("Database backup boshlandi...")
    print("=" * 50)
    if backup_database():
        print("=" * 50)
        print("[SUCCESS] Backup muvaffaqiyatli yakunlandi!")
    else:
        print("=" * 50)
        print("[ERROR] Backup yaratishda muammo!")
