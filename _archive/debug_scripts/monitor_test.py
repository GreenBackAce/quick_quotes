#!/usr/bin/env python3
"""
Monitor Quick Quotes Quill processing in real-time
Watches database and reports on meeting processing
"""

import time
import sqlite3
from datetime import datetime

DB_PATH = "meetings.db"

def get_meetings():
    """Get all meetings from database"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT meeting_id, title, created_at FROM meetings ORDER BY created_at DESC")
        meetings = cursor.fetchall()
        conn.close()
        return meetings
    except Exception as e:
        print(f"Error reading database: {e}")
        return []

def get_meeting_details(meeting_id):
    """Get full details for a meeting"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Get transcript count
        cursor.execute("SELECT COUNT(*) FROM transcripts WHERE meeting_id = ?", (meeting_id,))
        transcript_count = cursor.fetchone()[0]
        
        # Get summary
        cursor.execute("SELECT summary FROM summaries WHERE meeting_id = ?", (meeting_id,))
        summary_row = cursor.fetchone()
        has_summary = summary_row is not None
        
        conn.close()
        return transcript_count, has_summary
    except Exception as e:
        print(f"Error reading details: {e}")
        return 0, False

def monitor():
    """Monitor database for changes"""
    print("=" * 60)
    print("📊 MONITORING QUICK QUOTES QUILL")
    print("=" * 60)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("Watching for new meetings and processing updates...")
    print("=" * 60)
    
    last_meeting_count = 0
    known_meetings = set()
    
    while True:
        try:
            meetings = get_meetings()
            current_count = len(meetings)
            
            # New meeting detected
            if current_count > last_meeting_count:
                new_meetings = [m for m in meetings if m[0] not in known_meetings]
                for meeting_id, title, created_at in new_meetings:
                    print(f"\n🆕 NEW MEETING DETECTED")
                    print(f"   ID: {meeting_id[:8]}...")
                    print(f"   Title: {title}")
                    print(f"   Time: {created_at}")
                    known_meetings.add(meeting_id)
            
            # Check for updates on known meetings
            for meeting_id, title, created_at in meetings:
                if meeting_id in known_meetings:
                    transcript_count, has_summary = get_meeting_details(meeting_id)
                    
                    if transcript_count > 0:
                        print(f"\n📝 UPDATE: {title[:30]}...")
                        print(f"   Transcript: {transcript_count} segments")
                        print(f"   Summary: {'✅ Generated' if has_summary else '⏳ Pending'}")
            
            last_meeting_count = current_count
            time.sleep(2)  # Check every 2 seconds
            
        except KeyboardInterrupt:
            print("\n\n🛑 Monitoring stopped.")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}")
            time.sleep(2)

if __name__ == "__main__":
    monitor()
