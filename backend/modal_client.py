import modal
import sys
import os
import config

def process_remote_audio(audio_file_path: str):
    """
    Call the remote GPU worker to process the audio file.
    Returns the transcript list or None if failed.
    """
    print(f"🚀 Connecting to Remote GPU Worker ({config.config.MODAL_APP_NAME})...")
    
    try:
        # Look up the deployed class
        WorkerCls = modal.Cls.from_name(config.config.MODAL_APP_NAME, config.config.MODAL_CLASS_NAME)
        worker = WorkerCls()
        
        print(f"📤 Uploading {os.path.basename(audio_file_path)} to cloud...")
        
        # Read file
        with open(audio_file_path, "rb") as f:
            audio_data = f.read()
            
        # Call remote function
        print("⏳ Waiting for GPU processing...")
        result = worker.process_audio.remote(audio_data, os.path.basename(audio_file_path))
        
        if result["status"] == "success":
            print(f"✅ Remote processing complete! ({result['segments']} segments)")
            return result["transcript"]
        else:
            print(f"❌ Remote processing failed: {result['message']}")
            raise Exception(f"Remote processing failed: {result['message']}")
            
    except modal.exception.NotFoundError:
        error_msg = f"Could not find deployed worker '{config.config.MODAL_APP_NAME}'. Did you run 'modal deploy backend/modal_worker.py'?"
        print(f"❌ {error_msg}")
        raise Exception(error_msg)
    except Exception as e:
        print(f"❌ Error calling remote worker: {e}")
        raise e

if __name__ == "__main__":
    # Test block
    if len(sys.argv) < 2:
        print("Usage: python modal_client.py <audio_file>")
        sys.exit(1)
        
    audio_file = sys.argv[1]
    if not os.path.exists(audio_file):
        print(f"File {audio_file} not found")
        sys.exit(1)
        
    try:
        transcript = process_remote_audio(audio_file)
        if transcript:
            print("\n📝 Transcript Preview:")
            for i, segment in enumerate(transcript[:5], 1):
                print(f"{i}. [{segment['start']:.2f}s] {segment['speaker']}: {segment['text']}")
    except Exception as e:
        print(f"Test failed: {e}")
