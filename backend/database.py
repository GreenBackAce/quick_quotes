"""
Database management for Quick Quotes Quill
"""

import sqlite3
from datetime import datetime
from typing import List, Dict, Optional
import json

class DatabaseManager:
    def __init__(self, db_path: str = "meetings.db"):
        self.db_path = db_path

    def init_db(self):
        """Initialize database tables"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Create meetings table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS meetings (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # Create transcripts table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS transcripts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    meeting_id TEXT NOT NULL,
                    speaker TEXT,
                    text TEXT NOT NULL,
                    timestamp REAL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (meeting_id) REFERENCES meetings (id)
                )
            ''')

            # Create summaries table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS summaries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    meeting_id TEXT NOT NULL UNIQUE,
                    summary TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (meeting_id) REFERENCES meetings (id)
                )
            ''')

            conn.commit()

    def create_meeting(self, meeting_id: str, title: str) -> bool:
        """Create a new meeting record"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO meetings (id, title) VALUES (?, ?)",
                    (meeting_id, title)
                )
                conn.commit()
                return True
        except sqlite3.Error:
            return False

    def save_transcript(self, meeting_id: str, transcript: List[Dict]) -> bool:
        """Save transcript data for a meeting"""
        try:
            print(f"💾 Saving {len(transcript)} transcript segments for meeting {meeting_id}")
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                for idx, entry in enumerate(transcript):
                    # Use 'start' if available (from remote GPU), otherwise fall back to 'timestamp'
                    timestamp = entry.get("start", entry.get("timestamp", 0.0))
                    speaker = entry.get("speaker", "Unknown")
                    text = entry["text"]
                    
                    if idx < 3:
                        print(f"  [{idx}] Speaker: {speaker}, Time: {timestamp}, Text: {text[:50]}...")
                    
                    cursor.execute(
                        "INSERT INTO transcripts (meeting_id, speaker, text, timestamp) VALUES (?, ?, ?, ?)",
                        (meeting_id, speaker, text, timestamp)
                    )
                conn.commit()
                print(f"✅ Successfully saved {len(transcript)} segments")
                return True
        except sqlite3.Error as e:
            print(f"❌ Database error saving transcript: {e}")
            return False

    def save_summary(self, meeting_id: str, summary: str) -> bool:
        """Save summary for a meeting"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT OR REPLACE INTO summaries (meeting_id, summary) VALUES (?, ?)",
                    (meeting_id, summary)
                )
                conn.commit()
                return True
        except sqlite3.Error:
            return False

    def get_transcript(self, meeting_id: str) -> Optional[List[Dict]]:
        """Get transcript for a meeting"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT speaker, text, timestamp FROM transcripts WHERE meeting_id = ? ORDER BY timestamp",
                    (meeting_id,)
                )
                rows = cursor.fetchall()

                if not rows:
                    return None

                return [
                    {
                        "speaker": row[0],
                        "text": row[1],
                        "timestamp": row[2]
                    }
                    for row in rows
                ]
        except sqlite3.Error:
            return None

    def get_summary(self, meeting_id: str) -> Optional[str]:
        """Get summary for a meeting"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT summary FROM summaries WHERE meeting_id = ?",
                    (meeting_id,)
                )
                row = cursor.fetchone()
                return row[0] if row else None
        except sqlite3.Error:
            return None

    def list_meetings(self) -> List[Dict]:
        """List all meetings with their metadata"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT m.id, m.title, m.created_at,
                           COUNT(t.id) as transcript_count,
                           CASE WHEN s.summary IS NOT NULL THEN 1 ELSE 0 END as has_summary
                    FROM meetings m
                    LEFT JOIN transcripts t ON m.id = t.meeting_id
                    LEFT JOIN summaries s ON m.id = s.meeting_id
                    GROUP BY m.id, m.title, m.created_at, s.summary
                    ORDER BY m.created_at DESC
                """)
                rows = cursor.fetchall()

                return [
                    {
                        "id": row[0],
                        "title": row[1],
                        "created_at": row[2],
                        "transcript_count": row[3],
                        "has_summary": bool(row[4])
                    }
                    for row in rows
                ]
        except sqlite3.Error:
            return []

    def delete_meeting(self, meeting_id: str) -> bool:
        """Delete a meeting and all its associated data"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # Delete in correct order due to foreign keys
                cursor.execute("DELETE FROM summaries WHERE meeting_id = ?", (meeting_id,))
                cursor.execute("DELETE FROM transcripts WHERE meeting_id = ?", (meeting_id,))
                cursor.execute("DELETE FROM meetings WHERE id = ?", (meeting_id,))

                conn.commit()
                return cursor.rowcount > 0
        except sqlite3.Error:
            return False