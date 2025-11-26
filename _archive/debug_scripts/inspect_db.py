import sqlite3
import json
from datetime import datetime

def inspect_results():
    conn = sqlite3.connect('meetings.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Get the latest meeting
    cursor.execute("SELECT * FROM meetings ORDER BY created_at DESC LIMIT 1")
    meeting = cursor.fetchone()
    
    if not meeting:
        print("❌ No meetings found.")
        return

    print(f"📅 Meeting ID: {meeting['id']}")
    print(f"📝 Title: {meeting['title']}")
    print(f"🕒 Created At: {meeting['created_at']}")
    
    # Get transcript stats
    cursor.execute("SELECT * FROM transcripts WHERE meeting_id = ?", (meeting['id'],))
    transcripts = cursor.fetchall()
    print(f"📊 Transcript Segments: {len(transcripts)}")
    
    if transcripts:
        speakers = set(t['speaker'] for t in transcripts)
        print(f"👥 Speakers Identified: {speakers}")
        
        print("\n📝 First 5 Segments:")
        for t in transcripts[:5]:
            print(f"  [{t['speaker']}] ({t['timestamp']:.1f}s): {t['text'][:50]}...")
            
    # Get summary
    cursor.execute("SELECT * FROM summaries WHERE meeting_id = ?", (meeting['id'],))
    summary = cursor.fetchone()
    if summary:
        print(f"📋 Summary Keys: {summary.keys()}")
        # Try 'summary_text' or 'text' or just print the whole thing if small
        content = summary['summary_text'] if 'summary_text' in summary.keys() else str(dict(summary))
        print("\n📋 Summary Preview:")
        print(content[:200] + "...")
    else:
        print("\n❌ No summary found.")
        
    conn.close()

if __name__ == "__main__":
    inspect_results()
