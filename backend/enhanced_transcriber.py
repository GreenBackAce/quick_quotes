"""
Enhanced speech recognition with multiple engines and preprocessing
"""

import numpy as np
import torch
import torchaudio
import librosa
import noisereduce as nr
import webrtcvad
from typing import List, Dict, Optional, Tuple
import io
import tempfile
import os
from pathlib import Path
import speech_recognition as sr
from faster_whisper import WhisperModel
from scipy import signal
from scipy.io import wavfile

class EnhancedTranscriber:
    def __init__(self):
        self.recognizer = sr.Recognizer()

        # Initialize Whisper models (different sizes for different accuracy/speed trade-offs)
        self.whisper_models = {}
        self._load_whisper_models()

        # WebRTC VAD for voice activity detection
        self.vad = webrtcvad.Vad(3)  # Aggressiveness level 0-3

        # Audio preprocessing settings
        self.sample_rate = 16000
        self.channels = 1

        # Load configuration
        import config
        self.default_language = config.config.DEFAULT_LANGUAGE
        self.whisper_preference = config.config.WHISPER_MODEL_PREFERENCE
        self.enable_preprocessing = config.config.ENABLE_AUDIO_PREPROCESSING

        print("✅ Enhanced transcriber initialized with multiple engines")

    def _load_whisper_models(self):
        """Load available Whisper models using faster-whisper"""
        try:
            # Load configuration first
            import config
            model_name = config.config.WHISPER_MODEL_PREFERENCE
            
            # Auto-detect device
            device = "cuda" if torch.cuda.is_available() else "cpu"
            compute_type = "float16" if device == "cuda" else "int8"
            
            print(f"🔄 Loading Faster Whisper model: {model_name} on {device} with {compute_type}...")
            
            self.whisper_models[model_name] = WhisperModel(
                model_name, 
                device=device, 
                compute_type=compute_type
            )
            print(f"✅ Faster Whisper model '{model_name}' loaded successfully on {device}")
        except Exception as e:
            print(f"❌ Error loading Whisper models: {e}")

    def preprocess_audio(self, audio_data: bytes, sample_rate: int = 16000) -> Tuple[np.ndarray, int]:
        """
        Simplified audio preprocessing pipeline to avoid C-contiguous issues

        Args:
            audio_data: Raw audio bytes
            sample_rate: Original sample rate

        Returns:
            Tuple of (processed_audio_array, sample_rate)
        """
        try:
            # Convert bytes to numpy array and ensure C-contiguous
            audio_array = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32)
            audio_array = np.ascontiguousarray(audio_array)  # Ensure C-contiguous

            # Convert to mono if stereo
            if len(audio_array.shape) > 1:
                audio_array = np.mean(audio_array, axis=1)
                audio_array = np.ascontiguousarray(audio_array)

            # Normalize to [-1, 1]
            audio_array = audio_array / 32768.0

            # Resample to 16kHz if needed
            if sample_rate != self.sample_rate:
                audio_array = librosa.resample(audio_array, orig_sr=sample_rate, target_sr=self.sample_rate)
                audio_array = np.ascontiguousarray(audio_array)
                sample_rate = self.sample_rate

            # Apply band-pass filter (80Hz - 8000Hz) to remove rumble and hiss
            audio_array = self._band_pass_filter(audio_array, sample_rate)

            # Apply simple normalization (skip complex preprocessing to avoid errors)
            audio_array = self._simple_normalize_audio(audio_array)

            return audio_array, sample_rate

        except Exception as e:
            print(f"Warning: Audio preprocessing failed: {e}")
            # Return simple normalized audio if preprocessing fails
            try:
                simple_audio = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32) / 32768.0
                return np.ascontiguousarray(simple_audio), sample_rate
            except:
                # Last resort: return zeros
                return np.zeros(16000, dtype=np.float32), sample_rate

    def _band_pass_filter(self, audio: np.ndarray, sample_rate: int, low_cut: float = 80, high_cut: float = 8000) -> np.ndarray:
        """Apply band-pass filter to remove low-frequency rumble and high-frequency noise"""
        try:
            nyquist = sample_rate / 2
            low = low_cut / nyquist
            high = high_cut / nyquist
            
            # Design Butterworth filter
            b, a = signal.butter(4, [low, high], btype='band')
            
            # Apply filter
            filtered_audio = signal.filtfilt(b, a, audio)
            return filtered_audio.astype(np.float32)
        except Exception as e:
            print(f"Band-pass filter failed: {e}")
            return audio

    def _remove_noise_ai(self, audio_file_path: str) -> str:
        """
        Use Demucs to separate vocals from background noise.
        Returns path to the separated vocals file.
        """
        import config
        import subprocess
        import shutil
        
        if not config.config.ENABLE_AI_NOISE_REMOVAL:
            return audio_file_path
            
        print(f"🤖 Running AI Noise Removal (Demucs) on {audio_file_path}...")
        
        try:
            # Output directory for separation
            out_dir = Path(tempfile.gettempdir()) / "demucs_out"
            out_dir.mkdir(exist_ok=True)
            
            # Construct command
            # demucs --two-stems=vocals -n <model> -o <out_dir> <file>
            model = config.config.DEMUCS_MODEL
            cmd = [
                "demucs",
                "--two-stems=vocals",
                "-n", model,
                "-o", str(out_dir),
                audio_file_path
            ]
            
            # Run Demucs
            # We use the venv python to run the module if the direct command fails, 
            # but since we installed it, 'demucs' should be in the path or we can use 'python -m demucs'
            
            # Let's try running it as a subprocess
            process = subprocess.run(
                cmd,
                capture_output=True,
                text=True
            )
            
            if process.returncode != 0:
                print(f"❌ Demucs failed: {process.stderr}")
                return audio_file_path
                
            # Find the output file
            # Structure: <out_dir>/<model>/<filename_no_ext>/vocals.wav
            filename_no_ext = Path(audio_file_path).stem
            vocals_path = out_dir / model / filename_no_ext / "vocals.wav"
            
            if vocals_path.exists():
                print(f"✅ AI Noise Removal complete. Using processed file: {vocals_path}")
                return str(vocals_path)
            else:
                print(f"⚠️ Vocals file not found at {vocals_path}")
                return audio_file_path
                
        except Exception as e:
            print(f"❌ Error during AI noise removal: {e}")
            return audio_file_path
        """Apply noise reduction using spectral gating"""
        try:
            # Use noisereduce library for spectral gating
            reduced_noise = nr.reduce_noise(y=audio, sr=sample_rate, prop_decrease=0.8)
            return reduced_noise
        except Exception:
            return audio

    def _simple_normalize_audio(self, audio: np.ndarray) -> np.ndarray:
        """Apply simple audio normalization to avoid C-contiguous issues"""
        try:
            # Peak normalization (prevent clipping)
            max_val = np.max(np.abs(audio))
            if max_val > 0.95:
                audio = audio * (0.95 / max_val)
                audio = np.ascontiguousarray(audio)

            return audio
        except:
            return np.ascontiguousarray(audio)

    def _normalize_audio(self, audio: np.ndarray) -> np.ndarray:
        """Apply audio normalization"""
        # RMS normalization
        rms = np.sqrt(np.mean(audio**2))
        if rms > 0:
            target_rms = 0.1  # Target RMS level
            audio = audio * (target_rms / rms)

        # Peak normalization (prevent clipping)
        max_val = np.max(np.abs(audio))
        if max_val > 0.95:
            audio = audio * (0.95 / max_val)

        return audio

    def _high_pass_filter(self, audio: np.ndarray, sample_rate: int, cutoff: float = 80) -> np.ndarray:
        """Apply high-pass filter to remove low-frequency noise"""
        try:
            nyquist = sample_rate / 2
            normalized_cutoff = cutoff / nyquist

            # Design Butterworth filter
            b, a = signal.butter(4, normalized_cutoff, btype='high')

            # Apply filter
            filtered_audio = signal.filtfilt(b, a, audio)
            return filtered_audio
        except Exception:
            return audio

    def transcribe_enhanced(self, audio_data: bytes, use_whisper: bool = True, language: str = None) -> Dict:
        """
        Enhanced transcription with multiple engines and smart fallbacks
        
        Args:
            audio_data: Raw audio bytes
            use_whisper: Whether to try Whisper first
            language: Language code for recognition (uses config default if None)
            
        Returns:
            Best transcription result
        """
        if language is None:
            language = self.default_language

        # Always try Google as backup (with preprocessing)
        # Note: We removed the chunk-based Whisper transcription in favor of file-based faster-whisper
        # So for raw bytes, we default to Google or return an empty result if only Whisper is desired
        
        if not use_whisper:
             return self.transcribe_with_google(audio_data, language)

        # If we have raw bytes and want Whisper, we really should be using transcribe_file
        # But for compatibility, we'll try Google as a fallback for small chunks
        google_result = self.transcribe_with_google(audio_data, language)
        if google_result.get("text", "").strip():
            return google_result

        # No transcription succeeded
        return {
            "text": "",
            "confidence": 0.0,
            "engine": "none",
            "error": "All transcription engines failed"
        }

    def transcribe_file(self, audio_file_path: str, language: str = None) -> Dict:
        """
        Transcribe an entire audio file using Faster Whisper
        """
        if not self.whisper_models:
            return {"text": "", "confidence": 0.0, "segments": []}
            
        try:
            # Apply AI Noise Removal if enabled
            # This works on the file path, so we do it before loading the model or audio
            processed_file_path = self._remove_noise_ai(audio_file_path)
            
            print(f"📝 Transcribing file {processed_file_path} with Faster Whisper ({self.whisper_preference})...")
            model = self.whisper_models.get(self.whisper_preference)
            if not model:
                return {"text": "", "confidence": 0.0, "segments": []}
                
            print(f"🔍 DEBUG: About to call model.transcribe()...")
            # Enable word_timestamps=True to get word-level timing
            segments, info = model.transcribe(processed_file_path, language=language, beam_size=5, word_timestamps=True)
            print(f"🔍 DEBUG: Transcribe returned. Info: {info}")
            
            # faster-whisper returns a generator, so we need to iterate
            segment_list = list(segments)
            print(f"🔍 DEBUG: Segment list length: {len(segment_list)}")
            
            full_text = " ".join([segment.text for segment in segment_list])
            
            # Convert segments to our format
            formatted_segments = []
            for segment in segment_list:
                # Extract words if available
                words = []
                if hasattr(segment, 'words') and segment.words:
                    for word in segment.words:
                        words.append({
                            "word": word.word,
                            "start": word.start,
                            "end": word.end,
                            "probability": word.probability
                        })
                
                formatted_segments.append({
                    "start": segment.start,
                    "end": segment.end,
                    "text": segment.text.strip(),
                    "confidence": segment.avg_logprob,
                    "words": words  # Include word-level data
                })
                
            print(f"✅ Transcription complete: {len(formatted_segments)} segments")
            
            return {
                "text": full_text,
                "confidence": 1.0, 
                "segments": formatted_segments
            }
            
        except Exception as e:
            print(f"❌ Error transcribing file: {e}")
            return {"text": "", "confidence": 0.0, "segments": []}

    def get_audio_quality_metrics(self, audio_data: bytes) -> Dict:
        """
        Analyze audio quality metrics

        Args:
            audio_data: Raw audio bytes

        Returns:
            Dict with quality metrics
        """
        try:
            audio_array = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32)

            # Basic metrics
            rms = np.sqrt(np.mean(audio_array**2))
            peak = np.max(np.abs(audio_array))
            snr = self._estimate_snr(audio_array)

            return {
                "rms_level": float(rms),
                "peak_level": float(peak),
                "snr_estimate": float(snr),
                "quality_score": self._calculate_quality_score(rms, peak, snr)
            }

        except Exception as e:
            return {"error": str(e)}

    def _estimate_snr(self, audio: np.ndarray) -> float:
        """Estimate Signal-to-Noise Ratio"""
        try:
            # Simple SNR estimation using signal statistics
            signal_power = np.mean(audio**2)
            noise_power = np.var(audio) * 0.1  # Estimate noise as 10% of variance

            if noise_power > 0:
                snr = 10 * np.log10(signal_power / noise_power)
                return max(0, snr)  # Ensure non-negative
            return 0
        except:
            return 0

    def _calculate_quality_score(self, rms: float, peak: float, snr: float) -> float:
        """Calculate overall audio quality score (0-1)"""
        try:
            # Normalize metrics to 0-1 scale
            rms_score = min(1.0, rms / 10000)  # RMS level score
            peak_score = min(1.0, peak / 32767)  # Peak level score
            snr_score = min(1.0, snr / 30)  # SNR score (30dB is good)

            # Weighted average
            quality_score = (rms_score * 0.3 + peak_score * 0.3 + snr_score * 0.4)

            return round(quality_score, 2)

        except:
            return 0.0

    def detect_voice_activity(self, audio_data: bytes, frame_duration_ms: int = 30) -> List[bool]:
        """
        Detect voice activity using WebRTC VAD

        Args:
            audio_data: Raw audio bytes
            frame_duration_ms: Frame duration in milliseconds (10, 20, or 30)

        Returns:
            List of boolean values indicating voice activity for each frame
        """
        try:
            # Convert to 16-bit PCM
            audio_array = np.frombuffer(audio_data, dtype=np.int16)

            # Frame size calculation
            frame_size = int(self.sample_rate * frame_duration_ms / 1000)

            voice_activity = []

            # Process in frames
            for i in range(0, len(audio_array) - frame_size, frame_size):
                frame = audio_array[i:i + frame_size]

                # Convert to bytes for VAD
                frame_bytes = frame.tobytes()

                # Check for voice activity
                is_voice = self.vad.is_speech(frame_bytes, self.sample_rate)
                voice_activity.append(is_voice)

            return voice_activity

        except Exception as e:
            print(f"Voice activity detection failed: {e}")
            return []