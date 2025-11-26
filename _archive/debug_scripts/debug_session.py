import requests
import time
import os
import sys
import json
from datetime import datetime

# Configuration
BASE_URL = "http://localhost:8000"
TEST_FILE = "cb_test_short.wav"

def log(message, level="INFO"):
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] [{level}] {message}")

def run_debug_session():
    log(f"🚀 Starting Deep Debugging Session with {TEST_FILE}...")

    # 1. Check file existence
    if not os.path.exists(TEST_FILE):
        log(f"❌ Test file {TEST_FILE} not found!", "ERROR")
        return

    file_size = os.path.getsize(TEST_FILE) / (1024 * 1024)
    log(f"📁 File found: {TEST_FILE} ({file_size:.2f} MB)")

    # 2. Upload File
    log("📤 Uploading file to backend...")
    start_time = time.time()
    
    try:
        with open(TEST_FILE, "rb") as f:
            files = {"file": (TEST_FILE, f, "audio/wav")}
            data = {"meeting_title": f"Debug Session {datetime.now().strftime('%Y-%m-%d %H:%M')}"}
            response = requests.post(f"{BASE_URL}/meetings/upload", files=files, data=data, timeout=300)
            
        if response.status_code != 200:
            log(f"❌ Upload failed: {response.text}", "ERROR")
            return
            
        result = response.json()
        meeting_id = result.get("meeting_id")
        log(f"✅ Upload successful. Meeting ID: {meeting_id}")
        
    except Exception as e:
        log(f"❌ Upload exception: {e}", "ERROR")
        return

    # 3. Poll Progress
    log("🔄 Polling progress...")
    processing_start = time.time()
    
    while True:
        try:
            response = requests.get(f"{BASE_URL}/meetings/{meeting_id}/progress")
            if response.status_code == 200:
                data = response.json()
                progress = data.get("progress", 0)
                status = data.get("status", "Unknown")
                error = data.get("error")
                
                log(f"📊 Progress: {progress}% - {status}")
                
                if error:
                    log(f"❌ Processing Error: {error}", "ERROR")
                    break
                    
                if progress >= 100:
                    log("✅ Processing reported complete.")
                    break
            else:
                log(f"⚠️ Failed to get progress: {response.status_code}", "WARN")
                
            time.sleep(2)
            
        except Exception as e:
            log(f"❌ Polling exception: {e}", "ERROR")
            break

    processing_time = time.time() - processing_start
    log(f"⏱️ Total processing time: {processing_time:.2f} seconds")

    # 4. Retrieve Results
    log("📥 Retrieving final results...")
    try:
        response = requests.get(f"{BASE_URL}/meetings/{meeting_id}/transcript")
        if response.status_code == 200:
            data = response.json()
            transcript = data.get("transcript", [])
            summary = data.get("summary", "")
            
            # 5. Analyze Results
            log("🧐 Analyzing results...")
            log(f"   - Transcript Segments: {len(transcript)}")
            
            speakers = set()
            total_words = 0
            for entry in transcript:
                speakers.add(entry.get("speaker", "Unknown"))
                total_words += len(entry.get("text", "").split())
                
            log(f"   - Identified Speakers: {speakers}")
            log(f"   - Total Word Count: {total_words}")
            log(f"   - Summary Length: {len(summary)} chars")
            
            if len(transcript) > 0:
                log("   - First 3 segments:")
                for i in range(min(3, len(transcript))):
                    entry = transcript[i]
                    log(f"     [{entry.get('relative_time')}] {entry.get('speaker')}: {entry.get('text')[:50]}...")
            else:
                log("❌ Transcript is empty!", "ERROR")

            if not summary:
                log("❌ Summary is missing!", "ERROR")
            else:
                log("✅ Summary generated successfully.")
                
        else:
            log(f"❌ Failed to retrieve results: {response.text}", "ERROR")
            
    except Exception as e:
        log(f"❌ Result retrieval exception: {e}", "ERROR")

if __name__ == "__main__":
    run_debug_session()
