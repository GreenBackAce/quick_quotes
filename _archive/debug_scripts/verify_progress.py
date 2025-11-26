import requests
import time
import os

BASE_URL = "http://localhost:8000"
TEST_FILE = "test_audio.wav"

def create_dummy_wav():
    # Create a dummy WAV file if it doesn't exist
    if not os.path.exists(TEST_FILE):
        import wave
        import struct
        import math
        
        sample_rate = 16000
        duration = 5  # seconds
        frequency = 440.0
        
        print(f"Generating {duration}s dummy audio file...")
        with wave.open(TEST_FILE, 'w') as obj:
            obj.setnchannels(1)
            obj.setsampwidth(2)
            obj.setframerate(sample_rate)
            
            for i in range(int(sample_rate * duration)):
                value = int(32767.0 * math.sin(frequency * math.pi * 2 * i / sample_rate))
                data = struct.pack('<h', value)
                obj.writeframesraw(data)

def verify_progress():
    create_dummy_wav()
    
    print("🚀 Uploading file...")
    with open(TEST_FILE, 'rb') as f:
        files = {'file': (TEST_FILE, f, 'audio/wav')}
        response = requests.post(f"{BASE_URL}/meetings/upload", files=files)
    
    if response.status_code != 200:
        print(f"❌ Upload failed: {response.text}")
        return
        
    data = response.json()
    meeting_id = data['meeting_id']
    print(f"✅ Upload started. Meeting ID: {meeting_id}")
    
    print("🔄 Monitoring progress...")
    last_progress = -1
    
    while True:
        try:
            resp = requests.get(f"{BASE_URL}/meetings/{meeting_id}/progress")
            if resp.status_code == 200:
                prog_data = resp.json()
                progress = prog_data['progress']
                status = prog_data['status']
                
                if progress != last_progress:
                    print(f"📊 Progress: {progress}% - {status}")
                    last_progress = progress
                
                if progress >= 100:
                    print("✅ Processing complete!")
                    break
                
                if prog_data.get('error'):
                    print(f"❌ Error reported: {prog_data['error']}")
                    break
            else:
                print(f"⚠️ Failed to get progress: {resp.status_code}")
                
            time.sleep(1)
            
        except Exception as e:
            print(f"❌ Error polling progress: {e}")
            break

if __name__ == "__main__":
    verify_progress()
