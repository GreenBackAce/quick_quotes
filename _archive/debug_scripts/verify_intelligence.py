import requests
import json
import uuid
import time
from backend.database import DatabaseManager

# Initialize DB
db = DatabaseManager()
db.init_db()

# Create dummy meeting
meeting_id = str(uuid.uuid4())
title = "Intelligence Test Meeting"
db.create_meeting(meeting_id, title)

# Create dummy transcript
transcript = [
    {"speaker": "Alice", "text": "Welcome everyone to the project kickoff.", "start": 0, "end": 5},
    {"speaker": "Bob", "text": "Thanks Alice. I'm excited to work on the new AI features.", "start": 6, "end": 10},
    {"speaker": "Alice", "text": "Great. The main goal is to implement the chat interface by Friday.", "start": 11, "end": 15},
    {"speaker": "Charlie", "text": "I can handle the frontend work.", "start": 16, "end": 18},
    {"speaker": "Bob", "text": "I'll take care of the backend API.", "start": 19, "end": 22},
    {"speaker": "Alice", "text": "Perfect. Let's meet again on Wednesday to sync up.", "start": 23, "end": 27}
]
db.save_transcript(meeting_id, transcript)

print(f"✅ Created dummy meeting: {meeting_id}")

# Test Chat API
print("\n--- Testing Chat API ---")
question = "What is the main goal of the project?"
try:
    response = requests.post(
        f"http://localhost:8000/meetings/{meeting_id}/chat",
        json={"question": question}
    )
    if response.status_code == 200:
        print(f"Q: {question}")
        print(f"A: {response.json()['answer']}")
    else:
        print(f"❌ Chat failed: {response.text}")
except Exception as e:
    print(f"❌ Chat connection error: {e}")

# Test Analytics API
print("\n--- Testing Analytics API ---")
try:
    response = requests.get(f"http://localhost:8000/meetings/{meeting_id}/analytics")
    if response.status_code == 200:
        data = response.json()
        print("Talk Time:", json.dumps(data.get("talk_time"), indent=2))
        print("Sentiment:", json.dumps(data.get("sentiment"), indent=2))
    else:
        print(f"❌ Analytics failed: {response.text}")
except Exception as e:
    print(f"❌ Analytics connection error: {e}")

# Cleanup
db.delete_meeting(meeting_id)
print(f"\n✅ Cleaned up meeting {meeting_id}")
