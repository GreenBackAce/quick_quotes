import asyncio
import os
import sys
from backend.modal_client import process_remote_audio

# Ensure we can import backend
sys.path.append(os.getcwd())

async def main():
    audio_file = "cb_test_short.wav"
    if not os.path.exists(audio_file):
        print(f"File {audio_file} not found.")
        return

    print(f"Testing remote processing with {audio_file}...")
    try:
        # We need to bypass process_remote_audio's return value parsing to see the debug info
        # So we will import the worker class directly and call it, similar to how modal_client does it
        import modal
        import config
        
        print("🚀 Connecting to Modal app...")
        WorkerCls = modal.Cls.from_name(config.config.MODAL_APP_NAME, config.config.MODAL_CLASS_NAME)
        worker = WorkerCls()
        
        with open(audio_file, "rb") as f:
            audio_data = f.read()
            
        print("🚀 calling process_audio.remote()...")
        result = worker.process_audio.remote(audio_data, os.path.basename(audio_file))
        
        print("\n--- Debug Info ---")
        if "debug_info" in result:
            info = result["debug_info"]
            print(f"Transcript Segments: {info.get('transcript_segments')}")
            print(f"Diarization Segments: {info.get('diarization_segments')}")
            print(f"Has Words: {info.get('has_words')}")
            print(f"Audio Duration: {info.get('audio_duration')}")
            print(f"Raw Diarization: {info.get('diarization_raw')}")
        else:
            print("No debug info returned.")
            
        print(f"\nFinal Segments: {result.get('segments')}")
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
