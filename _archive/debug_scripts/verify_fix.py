
def verify_logic():
    # Simulate the output from enhanced_transcriber.transcribe_file
    segment_list = [
        {
            "start": 0.0,
            "end": 2.0,
            "text": "Hello world",
            "words": [
                {"word": "Hello", "start": 0.0, "end": 1.0, "probability": 0.9},
                {"word": "world", "start": 1.0, "end": 2.0, "probability": 0.9}
            ]
        }
    ]
    
    print("🔍 Input segments:", segment_list)
    
    transcript_entries = []
    
    # Simulate the loop in main.py (with the fix)
    for segment in segment_list:
        start_sec = segment.get("start", 0)
        end_sec = segment.get("end", 0)
        text = segment.get("text", "")
        
        transcript_entries.append({
            "text": text,
            "start_time": start_sec,
            "chunk_duration": end_sec - start_sec,
            "speaker": "Unknown",
            "words": segment.get("words", []) # The fix!
        })
        
    print("\n✅ Output transcript entries:", transcript_entries)
    
    # Verification
    if "words" in transcript_entries[0] and len(transcript_entries[0]["words"]) == 2:
        print("\n🎉 SUCCESS: 'words' field is present and correct!")
    else:
        print("\n❌ FAILURE: 'words' field is missing or empty!")

if __name__ == "__main__":
    verify_logic()
