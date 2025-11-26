import os
import sys
from pathlib import Path

# Check if running in Modal
# Version: Debug-v3
try:
    import modal
except ImportError:
    modal = None

# Define the image with dependencies
if modal:
    image = (
        modal.Image.from_registry("nvidia/cuda:12.2.0-devel-ubuntu22.04", add_python="3.10")
        .apt_install("git", "ffmpeg", "libsndfile1", "flac", "pkg-config", "build-essential", "python3-dev")
        .pip_install("setuptools", "wheel")  # Install build tools first
        .pip_install(
            "torch",
            "torchaudio",
            "numpy<2.0",
            "scipy",
            find_links="https://download.pytorch.org/whl/cu121"
        )
        .pip_install("nvidia-cudnn-cu12")
        .pip_install("faster-whisper")
        .pip_install("pyannote.audio")
        .pip_install("demucs")
        .pip_install("librosa")
        .pip_install("soundfile")
        .pip_install("noisereduce")
        .pip_install("SpeechRecognition")
        .pip_install("google-generativeai")
        .pip_install("python-dotenv")
        .pip_install("webrtcvad-wheels")
        .env({"LD_LIBRARY_PATH": "/usr/local/lib/python3.10/site-packages/nvidia/cudnn/lib:$LD_LIBRARY_PATH"})
        .add_local_dir("backend", remote_path="/root/backend")
        .add_local_file("config.py", remote_path="/root/config.py")
    )

    app = modal.App(
        "quick-quotes-worker", 
        image=image,
        secrets=[modal.Secret.from_name("my-dotenv-secret")]
    )
else:
    app = None
    image = None

# Define the GPU Worker class
# We use @app.cls to maintain state (loaded models) between calls
if app:
    @app.cls(gpu="A10G", timeout=1800, scaledown_window=300)
    class GPUWorker:
        def _load_models(self):
            """Helper to load models if not already loaded."""
            if hasattr(self, "transcriber") and self.transcriber is not None:
                return

            print("🔄 Loading models on GPU...")
            try:
                # Import here to avoid issues during image build
                # Ensure /root is in python path
                sys.path.append("/root")
                
                from backend.enhanced_transcriber import EnhancedTranscriber
                from backend.diarizer import SpeakerDiarizer
                import config
                
                # Initialize models
                # We force GPU usage here
                self.transcriber = EnhancedTranscriber()
                self.diarizer = SpeakerDiarizer()
                print("✅ Models loaded successfully!")
            except Exception as e:
                print(f"❌ Critical Error loading models: {e}")
                import traceback
                traceback.print_exc()
                raise e

        @modal.enter()
        def enter(self):
            # This runs when the container starts
            print("🟢 Container starting...")
            self._load_models()

        @modal.method()
        def process_audio(self, audio_data: bytes, filename: str):
            import tempfile
            import os
            
            print(f"🚀 Processing {filename} on Remote GPU (v2 - Fixed Arguments)...")
            
            # Lazy load safety net
            try:
                self._load_models()
            except Exception as e:
                return {"status": "error", "message": f"Model initialization failed: {str(e)}"}
            
            # Save audio to temp file
            with tempfile.NamedTemporaryFile(delete=False, suffix=Path(filename).suffix) as tmp:
                tmp.write(audio_data)
                tmp_path = tmp.name
            
            try:
                import torch
                import librosa
                print(f"🔍 GPU Status: Available={torch.cuda.is_available()}, Count={torch.cuda.device_count()}, Name={torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'None'}")
                
                y, sr = librosa.load(tmp_path, sr=None)
                print(f"🔍 Audio Stats: Duration={librosa.get_duration(y=y, sr=sr):.2f}s, Sample Rate={sr}, Shape={y.shape}")
                
                print("▶️ Starting Transcription...")
                # 1. Transcribe (with optional Demucs noise removal inside)
                transcript_result = self.transcriber.transcribe_file(tmp_path)
                print(f"   Transcription complete. Segments: {len(transcript_result['segments'])}")
                
                print("▶️ Starting Diarization...")
                # 2. Diarize
                diarization_segments = self.diarizer.diarize_audio_file(tmp_path)
                print(f"   Diarization complete. Segments: {len(diarization_segments)}")
                
                # Debug: Show unique speakers detected
                if diarization_segments:
                    unique_speakers = set(seg[2] for seg in diarization_segments if isinstance(seg, (list, tuple)) and len(seg) == 3)
                    print(f"   🔍 Pyannote detected speakers: {unique_speakers}")
                
                print("▶️ Aligning...")
                # Debug: Check transcript structure
                if transcript_result["segments"]:
                    first_seg = transcript_result["segments"][0]
                    print(f"   First segment keys: {first_seg.keys()}")
                    if "words" in first_seg:
                        print(f"   First segment word count: {len(first_seg['words'])}")
                    else:
                        print("   ⚠️ NO WORDS IN TRANSCRIPT SEGMENT!")

                # 3. Align
                final_transcript = self.diarizer.diarize_transcript(
                    transcript_result["segments"], 
                    diarization_segments=diarization_segments,
                    audio_file_path=tmp_path
                )
                
                print(f"🔍 FINAL TRANSCRIPT: {len(final_transcript)} segments")
                if final_transcript:
                    for i, seg in enumerate(final_transcript[:3]):
                        print(f"  [{i}] {seg.get('speaker', 'N/A')}: {seg.get('text', '')[:50]}...")
                
                return {
                    "status": "success",
                    "transcript": final_transcript,
                    "segments": len(final_transcript),
                    "debug_info": {
                        "transcript_segments": len(transcript_result["segments"]),
                        "diarization_segments": len(diarization_segments),
                        "has_words": "words" in transcript_result["segments"][0] if transcript_result["segments"] else False,
                        "audio_duration": librosa.get_duration(y=y, sr=sr),
                        "diarization_raw": [str(s) for s in diarization_segments]
                    }
                }
                
            except Exception as e:
                print(f"❌ Error processing on GPU: {e}")
                import traceback
                traceback.print_exc()
                return {"status": "error", "message": str(e)}
            finally:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)

# For local testing/simulation
if __name__ == "__main__":
    print("This script is intended to be run with 'modal run backend/modal_worker.py'")
