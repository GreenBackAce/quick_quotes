import asyncio
import os
from backend.enhanced_transcriber import EnhancedTranscriber
from backend.diarizer import SpeakerDiarizer

async def verify():
    print("🚀 Starting Word-Level Timestamp Verification...")
    
    wav_path = "test_snippet.wav"
    if not os.path.exists(wav_path):
        print(f"❌ Test file {wav_path} not found!")
        return

    # Initialize components
    transcriber = EnhancedTranscriber()
    diarizer = SpeakerDiarizer()
    
    # 1. Transcribe with word timestamps
    print("\n📝 Transcribing...")
    transcript_result = await asyncio.to_thread(transcriber.transcribe_file, wav_path)
    raw_segments = transcript_result["segments"]
    print(f"✅ Raw Whisper Segments: {len(raw_segments)}")
    
    # Check if words are present
    has_words = any("words" in seg and seg["words"] for seg in raw_segments)
    if has_words:
        print("✅ Word timestamps found in transcript!")
    else:
        print("❌ NO word timestamps found!")
        return

    # 2. Diarize
    print("\n👥 Diarizing...")
    diarization_segments = await asyncio.to_thread(diarizer.diarize_audio_file, wav_path)
    print(f"✅ Diarization Segments: {len(diarization_segments)}")

    # 3. Align (using new word-level logic)
    print("\n🔗 Aligning...")
    final_transcript = diarizer.diarize_transcript(transcript_result["segments"], diarization_segments, wav_path)
    
    print(f"\n✅ Final Transcript Segments: {len(final_transcript)}")
    
    # Print first few segments to verify
    print("\n--- First 5 Segments ---")
    for i, seg in enumerate(final_transcript[:5]):
        print(f"[{seg['start']:.2f} - {seg['end']:.2f}] {seg['speaker']}: {seg['text']}")

if __name__ == "__main__":
    asyncio.run(verify())
