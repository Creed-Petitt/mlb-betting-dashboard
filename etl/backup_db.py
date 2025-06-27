#!/usr/bin/env python3
"""
Database backup utility for MLB Bet AI
Creates timestamped backups of the SQLite database
"""

import os
import sys
import shutil
import sqlite3
from datetime import datetime

def backup_database():
    """Create a timestamped backup of the database"""
    
    # Get database path
    db_path = os.path.abspath("data/mlb.db")
    
    if not os.path.exists(db_path):
        print(f"[ERROR] Database not found at {db_path}")
        return False
    
    # Create backup filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = f"data/mlb.db.backup.{timestamp}"
    
    try:
        # First check database integrity
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("PRAGMA integrity_check;")
        result = cursor.fetchone()
        conn.close()
        
        if result[0] != "ok":
            print(f"[ERROR] Database integrity check failed: {result[0]}")
            return False
        
        # Create backup
        shutil.copy2(db_path, backup_path)
        
        # Verify backup
        conn = sqlite3.connect(backup_path)
        cursor = conn.cursor()
        cursor.execute("PRAGMA integrity_check;")
        result = cursor.fetchone()
        conn.close()
        
        if result[0] != "ok":
            print(f"[ERROR] Backup integrity check failed: {result[0]}")
            os.remove(backup_path)
            return False
        
        backup_size = os.path.getsize(backup_path)
        print(f"[SUCCESS] Database backed up to: {backup_path} ({backup_size:,} bytes)")
        
        # Clean up old backups (keep last 10)
        cleanup_old_backups()
        
        return True
        
    except Exception as e:
        print(f"[ERROR] Backup failed: {e}")
        return False

def cleanup_old_backups():
    """Keep only the 10 most recent backups"""
    
    data_dir = "data"
    backup_files = []
    
    for filename in os.listdir(data_dir):
        if filename.startswith("mlb.db.backup.") and filename != "mlb.db.backup.20250623_015534":
            filepath = os.path.join(data_dir, filename)
            backup_files.append(filepath)
    
    # Sort by modification time (newest first)
    backup_files.sort(key=os.path.getmtime, reverse=True)
    
    # Remove files beyond the 10 most recent
    for old_backup in backup_files[10:]:
        try:
            os.remove(old_backup)
            print(f"[CLEANUP] Removed old backup: {os.path.basename(old_backup)}")
        except Exception as e:
            print(f"[WARN] Failed to remove old backup {old_backup}: {e}")

if __name__ == "__main__":
    success = backup_database()
    sys.exit(0 if success else 1) 