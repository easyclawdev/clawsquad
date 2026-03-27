#!/usr/bin/env python3
"""
ClawSquad SQLite Backup Script
Creates daily backups, keeps 7 days of backups
"""

import sqlite3
import shutil
import os
import sys
from datetime import datetime, timedelta
import gzip
import json
from pathlib import Path

class ClawSquadBackup:
    def __init__(self, db_path="clawsquad.db", backup_dir="backups"):
        self.db_path = db_path
        self.backup_dir = Path(backup_dir)
        self.backup_dir.mkdir(exist_ok=True)
        
    def create_backup(self):
        """Create a timestamped backup of the SQLite database"""
        if not os.path.exists(self.db_path):
            print(f"Database file not found: {self.db_path}")
            return False
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"clawsquad_backup_{timestamp}.db.gz"
        backup_path = self.backup_dir / backup_name
        
        try:
            # Create a connection to the database
            conn = sqlite3.connect(self.db_path)
            
            # Create backup using SQLite backup API (more reliable than file copy)
            backup_conn = sqlite3.connect(':memory:')
            conn.backup(backup_conn)
            backup_conn.close()
            conn.close()
            
            # For simplicity, we'll use file copy for now
            # In production, consider using the backup API properly
            with open(self.db_path, 'rb') as f_in:
                with gzip.open(backup_path, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)
            
            # Create metadata file
            metadata = {
                "timestamp": datetime.now().isoformat(),
                "backup_file": backup_name,
                "original_size": os.path.getsize(self.db_path),
                "compressed_size": os.path.getsize(backup_path),
                "database_version": self.get_db_version()
            }
            
            metadata_path = self.backup_dir / f"clawsquad_backup_{timestamp}.meta.json"
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f, indent=2)
            
            print(f"✅ Backup created: {backup_name} ({metadata['compressed_size']} bytes)")
            print(f"   Metadata: {metadata_path.name}")
            
            return True
            
        except Exception as e:
            print(f"❌ Backup failed: {e}")
            return False
    
    def get_db_version(self):
        """Get database schema version"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get table counts
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = cursor.fetchall()
            
            # Get row counts for main tables
            stats = {}
            for table in tables:
                table_name = table[0]
                cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                count = cursor.fetchone()[0]
                stats[table_name] = count
            
            conn.close()
            return stats
            
        except Exception as e:
            return {"error": str(e)}
    
    def rotate_backups(self, keep_days=7):
        """Remove backups older than keep_days"""
        cutoff_date = datetime.now() - timedelta(days=keep_days)
        deleted_count = 0
        
        for backup_file in self.backup_dir.glob("clawsquad_backup_*.db.gz"):
            # Extract timestamp from filename
            try:
                # Format: clawsquad_backup_YYYYMMDD_HHMMSS.db.gz
                timestamp_str = backup_file.stem.replace("clawsquad_backup_", "").replace(".db", "")
                file_date = datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S")
                
                if file_date < cutoff_date:
                    # Also delete corresponding metadata file
                    meta_file = self.backup_dir / f"clawsquad_backup_{timestamp_str}.meta.json"
                    
                    backup_file.unlink()
                    if meta_file.exists():
                        meta_file.unlink()
                    
                    deleted_count += 1
                    print(f"🗑️  Deleted old backup: {backup_file.name}")
                    
            except ValueError:
                # Skip files with invalid names
                continue
        
        print(f"📊 Rotation complete: Deleted {deleted_count} old backups")
        return deleted_count
    
    def list_backups(self):
        """List all available backups"""
        backups = []
        
        for backup_file in sorted(self.backup_dir.glob("clawsquad_backup_*.db.gz")):
            try:
                timestamp_str = backup_file.stem.replace("clawsquad_backup_", "").replace(".db", "")
                file_date = datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S")
                
                meta_file = self.backup_dir / f"clawsquad_backup_{timestamp_str}.meta.json"
                metadata = {}
                if meta_file.exists():
                    with open(meta_file, 'r') as f:
                        metadata = json.load(f)
                
                backups.append({
                    "filename": backup_file.name,
                    "date": file_date.isoformat(),
                    "size": os.path.getsize(backup_file),
                    "metadata": metadata
                })
                
            except ValueError:
                continue
        
        return backups
    
    def restore_backup(self, backup_filename):
        """Restore database from a backup"""
        backup_path = self.backup_dir / backup_filename
        
        if not backup_path.exists():
            print(f"❌ Backup file not found: {backup_filename}")
            return False
        
        try:
            # Create backup of current database before restore
            if os.path.exists(self.db_path):
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                pre_restore_backup = f"pre_restore_{timestamp}.db"
                shutil.copy2(self.db_path, self.backup_dir / pre_restore_backup)
                print(f"📋 Created pre-restore backup: {pre_restore_backup}")
            
            # Extract and restore
            with gzip.open(backup_path, 'rb') as f_in:
                with open(self.db_path, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)
            
            print(f"✅ Database restored from: {backup_filename}")
            return True
            
        except Exception as e:
            print(f"❌ Restore failed: {e}")
            return False
    
    def get_backup_stats(self):
        """Get backup statistics"""
        backups = self.list_backups()
        
        if not backups:
            return {"total_backups": 0, "total_size": 0, "oldest": None, "newest": None}
        
        total_size = sum(b["size"] for b in backups)
        oldest = min(b["date"] for b in backups)
        newest = max(b["date"] for b in backups)
        
        return {
            "total_backups": len(backups),
            "total_size": total_size,
            "total_size_human": self._human_readable_size(total_size),
            "oldest_backup": oldest,
            "newest_backup": newest,
            "backups": backups
        }
    
    def _human_readable_size(self, size):
        """Convert bytes to human readable format"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.2f} {unit}"
            size /= 1024.0
        return f"{size:.2f} TB"

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="ClawSquad SQLite Backup Manager")
    parser.add_argument("action", choices=["create", "rotate", "list", "stats", "restore"],
                       help="Action to perform")
    parser.add_argument("--db-path", default="clawsquad.db",
                       help="Path to SQLite database (default: clawsquad.db)")
    parser.add_argument("--backup-dir", default="backups",
                       help="Backup directory (default: backups)")
    parser.add_argument("--keep-days", type=int, default=7,
                       help="Number of days to keep backups (default: 7)")
    parser.add_argument("--restore-file",
                       help="Backup filename to restore (for restore action)")
    
    args = parser.parse_args()
    
    backup_manager = ClawSquadBackup(args.db_path, args.backup_dir)
    
    if args.action == "create":
        success = backup_manager.create_backup()
        if success:
            backup_manager.rotate_backups(args.keep_days)
        sys.exit(0 if success else 1)
        
    elif args.action == "rotate":
        deleted = backup_manager.rotate_backups(args.keep_days)
        sys.exit(0)
        
    elif args.action == "list":
        backups = backup_manager.list_backups()
        if backups:
            print("📋 Available backups:")
            for backup in backups:
                print(f"  • {backup['filename']}")
                print(f"    Date: {backup['date']}")
                print(f"    Size: {backup_manager._human_readable_size(backup['size'])}")
                if backup['metadata']:
                    print(f"    Tables: {backup['metadata'].get('database_version', {})}")
                print()
        else:
            print("📭 No backups found")
            
    elif args.action == "stats":
        stats = backup_manager.get_backup_stats()
        print("📊 Backup Statistics:")
        print(f"  Total backups: {stats['total_backups']}")
        print(f"  Total size: {stats['total_size_human']}")
        print(f"  Oldest backup: {stats['oldest_backup'] or 'N/A'}")
        print(f"  Newest backup: {stats['newest_backup'] or 'N/A'}")
        
    elif args.action == "restore":
        if not args.restore_file:
            print("❌ Please specify --restore-file")
            sys.exit(1)
        success = backup_manager.restore_backup(args.restore_file)
        sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()