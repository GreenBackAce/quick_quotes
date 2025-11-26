import asyncio
import os
import config
from backend.enhanced_transcriber import EnhancedTranscriber

# Force enable AI Noise Removal for this test
config.config.ENABLE_AI_NOISE_REMOVAL = True
config.config.DEMUCS_MODEL = "htdemucs"

async def verify():
    print("🚀 Starting AI Noise Removal Verification...")
    print(f"Config ENABLE_AI_NOISE_REMOVAL: {config.config.ENABLE_AI_NOISE_REMOVAL}")
    
    wav_path = "test_snippet.wav"
    if not os.path.exists(wav_path):
        print(f"❌ Test file {wav_path} not found!")
        return

    # Initialize transcriber
    transcriber = EnhancedTranscriber()
    
    # Run transcription (which should trigger noise removal)
    print("\n📝 Transcribing (with Demucs)...")
    # Note: This is synchronous in the class, so we can call it directly or via asyncio.to_thread
    # But since we are in a script, direct call is fine.
    
    try:
        result = transcriber.transcribe_file(wav_path)
        print(f"✅ Transcription complete: {len(result['segments'])} segments")
        print("Check logs above for 'Running AI Noise Removal' and 'Demucs' output.")
    except Exception as e:
        print(f"❌ Verification failed: {e}")

if __name__ == "__main__":
    asyncio.run(verify())
