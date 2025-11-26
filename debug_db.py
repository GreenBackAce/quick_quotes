import sqlite3
import json
import os

db_path = "meetings.db"

if not os.path.exists(db_path):
    print("❌ Database not found!")
    exit(1)

conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

# Get columns
cursor.execute("PRAGMA table_info(meetings)")
columns = [row['name'] for row in cursor.fetchall()]
print(f"Columns: {columns}")

# Get latest meeting
cursor.execute("SELECT * FROM meetings ORDER BY created_at DESC LIMIT 1")
meeting = cursor.fetchone()

if not meeting:
    print("❌ No meetings found.")
else:
    meeting_id = meeting['id']
    print(f"✅ Latest Meeting ID: {meeting_id}")
    print(f"   Created At: {meeting['created_at']}")
    
    # Get transcript segments
    cursor.execute("SELECT * FROM transcripts WHERE meeting_id = ? ORDER BY timestamp", (meeting_id,))
    segments = cursor.fetchall()
    
    print(f"   Segment Count: {len(segments)}")
    
    print("\n--- First 5 Segments ---")
    for i, seg in enumerate(segments[:5]):
        print(f"[{i}] Speaker: {seg['speaker']}")
        print(f"    Time: {seg['timestamp']:.2f}")
        print(f"    Text: {seg['text'][:100]}...")
        print("-" * 20)

conn.close()
