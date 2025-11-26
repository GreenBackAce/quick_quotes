import os
import torch
import torchaudio

# Monkey patch for torchaudio < 2.1 compatibility required by speechbrain
if not hasattr(torchaudio, "list_audio_backends"):
    print("🔧 Patching torchaudio.list_audio_backends for speechbrain compatibility")
    torchaudio.list_audio_backends = lambda: ["soundfile"]
    torchaudio.set_audio_backend = lambda x: None
    torchaudio.get_audio_backend = lambda: "soundfile"

from pyannote.audio import Pipeline
import config
from pydub import AudioSegment

def debug_diarization():
    print("🐛 Starting PyAnnote Debug...")
    
    # Check Token
    token = config.config.HUGGINGFACE_TOKEN
    print(f"🔑 Token present: {bool(token)}")
    if token:
        print(f"🔑 Token length: {len(token)}")
        print(f"🔑 Token start: {token[:4]}...")
        
        try:
            from huggingface_hub import whoami
            user_info = whoami(token=token)
            print(f"👤 Token belongs to: {user_info.get('name', 'Unknown')}")
            print(f"   Org memberships: {', '.join([org['name'] for org in user_info.get('orgs', [])])}")
        except Exception as e:
            print(f"❌ Token validation failed: {e}")
            return
    
    # Create a dummy audio file with clear speaker change
    # 5 seconds of 440Hz tone, 5 seconds of silence, 5 seconds of 880Hz tone
    print("🎵 Creating test audio...")
    from pydub.generators import Sine
    
    sound1 = Sine(440).to_audio_segment(duration=3000)
    silence = AudioSegment.silent(duration=1000)
    sound2 = Sine(880).to_audio_segment(duration=3000)
    
    audio = sound1 + silence + sound2
    test_file = "debug_audio.wav"
    audio.export(test_file, format="wav")
    print(f"✅ Created {test_file}")
    
    # Initialize Pipeline
    print("🔄 Initializing Pipeline...")
    try:
        pipeline = Pipeline.from_pretrained(
            "pyannote/speaker-diarization-3.1",
            token=token
        )
        
        if torch.cuda.is_available():
            pipeline.to(torch.device("cuda"))
            print("✅ Using GPU")
        else:
            print("✅ Using CPU")
            
        # Run
        print("🏃 Running diarization...")
        diarization = pipeline(test_file)
        
        print(f"📦 Output type: {type(diarization)}")
        print(f"📦 Output dir: {dir(diarization)}")
        
        # Try to handle it based on inspection (it might be a tuple or object with annotation)
        annotation = diarization
        if hasattr(diarization, "annotation"):
             annotation = diarization.annotation
        elif isinstance(diarization, tuple):
             # Maybe (annotation, ...)
             annotation = diarization[0]
             
        segments = []
        if hasattr(annotation, "itertracks"):
            for turn, _, speaker in annotation.itertracks(yield_label=True):
                print(f"  🗣️  {turn.start:.1f}s - {turn.end:.1f}s: {speaker}")
                segments.append(speaker)
        else:
            print(f"❌ Could not find annotation in output")
            
        print(f"✅ Found {len(segments)} segments")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_diarization()
