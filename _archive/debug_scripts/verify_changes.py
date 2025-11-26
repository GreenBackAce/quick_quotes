import os
import sys
import shutil
import tempfile
from backend.main import process_uploaded_audio
from backend.database import DatabaseManager

def verify():
    # Setup
    print("🚀 Starting verification...")
    
    # Use the sample file
    sample_file = "Special Meeting Audio File - April 29, 2025.mp3"
    if not os.path.exists(sample_file):
        print(f"❌ Sample file {sample_file} not found!")
        return

    # Create a temp copy to simulate upload
    temp_dir = tempfile.mkdtemp()
    temp_file_path = os.path.join(temp_dir, "test_audio.mp3")
    shutil.copy(sample_file, temp_file_path)
    
    meeting_id = "test_meeting_verification"
    
    # Initialize DB
    db = DatabaseManager()
    db.init_db()
    db.create_meeting(meeting_id, "Verification Meeting")
    
    try:
        # Run processing
        print(f"🎧 Processing {temp_file_path}...")
        process_uploaded_audio(meeting_id, temp_file_path, temp_dir)
        
        # Check results
        transcript = db.get_transcript(meeting_id)
        summary = db.get_summary(meeting_id)
        
        if not transcript:
            print("❌ No transcript generated!")
        else:
            print(f"✅ Transcript generated with {len(transcript)} segments.")
            
            # Check for speakers
            speakers = set(entry.get("speaker") for entry in transcript)
            print(f"👥 Speakers found: {speakers}")
            
            if len(speakers) > 1 and "Speaker 1" not in speakers:
                 print("✅ Diarization seems to be working (multiple speakers found).")
            elif "Speaker 1" in speakers and len(speakers) == 1:
                 print("⚠️  Only 'Speaker 1' found. Diarization might have failed or fell back.")
            
            # Print first few lines
            print("\n📝 First 3 transcript entries:")
            for entry in transcript[:3]:
                print(f"  [{entry['speaker']}] {entry['text'][:50]}...")
                
        if summary:
            print("\n✅ Summary generated.")
        else:
            print("\n⚠️  No summary generated.")
            
    except Exception as e:
        print(f"❌ Verification failed with error: {e}")
    finally:
        # Cleanup
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
            
if __name__ == "__main__":
    verify()
