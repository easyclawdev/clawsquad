#!/usr/bin/env python3
"""
Test the backup system locally before deploying to server
"""

import os
import tempfile
import shutil
from pathlib import Path
import sqlite3

def create_test_database(db_path):
    """Create a test SQLite database with sample data"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create test tables similar to ClawSquad
    cursor.execute('''
    CREATE TABLE agents (
        agent_id TEXT PRIMARY KEY,
        online_status TEXT DEFAULT 'offline',
        last_seen TIMESTAMP
    )
    ''')
    
    cursor.execute('''
    CREATE TABLE messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        agent_id TEXT NOT NULL,
        content TEXT NOT NULL,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # Insert test data
    cursor.execute("INSERT INTO agents (agent_id, online_status) VALUES ('test_agent_1', 'online')")
    cursor.execute("INSERT INTO agents (agent_id, online_status) VALUES ('test_agent_2', 'offline')")
    cursor.execute("INSERT INTO messages (agent_id, content) VALUES ('test_agent_1', 'Hello world!')")
    cursor.execute("INSERT INTO messages (agent_id, content) VALUES ('test_agent_2', 'Backup test message')")
    
    conn.commit()
    conn.close()
    
    print(f"✅ Created test database at {db_path}")
    return db_path

def test_backup_system():
    """Test the backup system in a temporary directory"""
    with tempfile.TemporaryDirectory() as tmpdir:
        print(f"📁 Testing in temporary directory: {tmpdir}")
        
        # Create test database
        test_db = Path(tmpdir) / "test.db"
        create_test_database(test_db)
        
        # Import and test backup module
        import sys
        sys.path.insert(0, str(Path(__file__).parent))
        
        from backup import ClawSquadBackup
        
        # Create backup manager
        backup_dir = Path(tmpdir) / "backups"
        backup_manager = ClawSquadBackup(str(test_db), str(backup_dir))
        
        # Test 1: Create backup
        print("\n🧪 Test 1: Creating backup...")
        success = backup_manager.create_backup()
        assert success, "Backup creation failed"
        
        # Test 2: List backups
        print("\n🧪 Test 2: Listing backups...")
        backups = backup_manager.list_backups()
        assert len(backups) == 1, f"Expected 1 backup, got {len(backups)}"
        print(f"   Found {len(backups)} backup(s)")
        
        # Test 3: Get stats
        print("\n🧪 Test 3: Getting statistics...")
        stats = backup_manager.get_backup_stats()
        assert stats['total_backups'] == 1, f"Expected 1 backup in stats, got {stats['total_backups']}"
        print(f"   Stats: {stats}")
        
        # Test 4: Create multiple backups
        print("\n🧪 Test 4: Creating additional backups...")
        for i in range(2):
            # Modify database slightly
            conn = sqlite3.connect(test_db)
            cursor = conn.cursor()
            cursor.execute(f"INSERT INTO messages (agent_id, content) VALUES ('test_agent_{i}', 'Additional message {i}')")
            conn.commit()
            conn.close()
            
            success = backup_manager.create_backup()
            assert success, f"Additional backup {i+1} failed"
        
        backups = backup_manager.list_backups()
        print(f"   Total backups: {len(backups)}")
        
        # Test 5: Restore backup (simulated)
        print("\n🧪 Test 5: Testing restore capability...")
        if backups:
            backup_file = backups[0]['filename']
            print(f"   Would restore from: {backup_file}")
            # In actual test, we would restore to a different file
            # For now, just verify the file exists
            backup_path = backup_dir / backup_file
            assert backup_path.exists(), f"Backup file doesn't exist: {backup_path}"
        
        print("\n🎉 All tests passed!")
        return True

if __name__ == "__main__":
    try:
        test_backup_system()
        print("\n✅ Backup system test completed successfully")
        print("\nNext steps:")
        print("1. Deploy to server: scp backup.py backup.sh systemd/* user@server:/opt/clawsquad/")
        print("2. Make scripts executable: chmod +x backup.sh")
        print("3. Test on server: python3 backup.py create")
        print("4. Set up automation: systemctl enable clawsquad-backup.timer")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        exit(1)