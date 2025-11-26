"""
Audio processing module for real-time meeting recording and transcription
"""

import speech_recognition as sr
from typing import List, Dict, Optional, Callable
import threading
import time
import queue
import numpy as np
from datetime import datetime
from .enhanced_transcriber import EnhancedTranscriber

# Try to import pyaudio, but handle gracefully if not available
try:
    import pyaudio
    PYAUDIO_AVAILABLE = True
except ImportError:
    PYAUDIO_AVAILABLE = False
    print("Warning: PyAudio not available. Audio recording may be limited.")

# Make PYAUDIO_AVAILABLE available globally in this module

class AudioProcessor:
    def __init__(self):
        self.recognizer = sr.Recognizer()
        self.enhanced_transcriber = EnhancedTranscriber()

        # Try to initialize microphone, but handle gracefully if PyAudio is not available
        self.microphone = None
        if PYAUDIO_AVAILABLE:
            try:
                self.microphone = sr.Microphone()
            except Exception as e:
                print(f"Warning: Could not initialize microphone: {e}")
                # Don't modify global PYAUDIO_AVAILABLE here, just set local flag
                self.microphone = None

        # Audio settings
        self.chunk_size = 1024
        self.sample_rate = 16000
        self.channels = 1
        if PYAUDIO_AVAILABLE:
            import pyaudio
            self.format = pyaudio.paInt16
        else:
            self.format = None

        # Recording state
        self.is_recording = False
        self.current_meeting_id = None
        self.audio_queue = queue.Queue()
        self.transcript = []
        self.recording_thread = None

        # Callbacks
        self.on_transcript_update = None  # Callback for real-time transcript updates

        # Adjust for ambient noise if microphone is available
        if self.microphone:
            try:
                print("Adjusting for ambient noise... Please wait.")
                with self.microphone as source:
                    self.recognizer.adjust_for_ambient_noise(source, duration=1)
                print("Audio processor initialized.")
            except Exception as e:
                print(f"Warning: Could not adjust for ambient noise: {e}")
        else:
            print("Audio processor initialized (limited functionality - no microphone access).")

    def start_recording(self, meeting_id: str):
        """Start recording audio for a meeting"""
        if self.is_recording:
            print("Already recording a meeting")
            return

        self.is_recording = True
        self.current_meeting_id = meeting_id
        self.transcript = []

        print(f"🎤 Started recording for meeting {meeting_id}")

        # Start recording thread
        self.recording_thread = threading.Thread(target=self._record_audio)
        self.recording_thread.daemon = True
        self.recording_thread.start()

        # Start transcription thread
        transcription_thread = threading.Thread(target=self._process_audio_queue)
        transcription_thread.daemon = True
        transcription_thread.start()

        print("🎵 Audio recording and transcription threads started")

    def stop_recording(self, meeting_id: str) -> List[Dict]:
        """Stop recording and return the transcript"""
        if not self.is_recording or self.current_meeting_id != meeting_id:
            print("No active recording for this meeting")
            return []

        self.is_recording = False

        # Wait for recording thread to finish
        if self.recording_thread and self.recording_thread.is_alive():
            self.recording_thread.join(timeout=5)

        # Process any remaining audio in queue
        self._process_audio_queue()

        transcript = self.transcript.copy()
        self.transcript = []
        self.current_meeting_id = None

        print(f"🛑 Stopped recording for meeting {meeting_id}")
        print(f"📝 Final transcript contains {len(transcript)} entries")
        return transcript

    def _record_audio(self):
        """Record audio from microphone and put in queue"""
        if not PYAUDIO_AVAILABLE:
            print("PyAudio not available. Using SpeechRecognition microphone input instead.")
            self._record_with_speech_recognition()
            return

        audio = pyaudio.PyAudio()

        try:
            stream = audio.open(
                format=self.format,
                channels=self.channels,
                rate=self.sample_rate,
                input=True,
                frames_per_buffer=self.chunk_size
            )

            print("Recording started...")

            while self.is_recording:
                try:
                    data = stream.read(self.chunk_size, exception_on_overflow=False)
                    self.audio_queue.put(data)
                except Exception as e:
                    print(f"Error reading audio: {e}")
                    break

            stream.stop_stream()
            stream.close()

        except Exception as e:
            print(f"Error opening audio stream: {e}")
            # Fallback to SpeechRecognition
            self._record_with_speech_recognition()
        finally:
            audio.terminate()

        print("Recording stopped.")

    def _record_with_speech_recognition(self):
        """Fallback recording method using SpeechRecognition's listen()"""
        print("Using SpeechRecognition for audio input...")

        try:
            # Use the default microphone if available, otherwise use None for default
            source = self.microphone if self.microphone else None

            if source is None:
                print("No microphone available, trying default...")
                # Try to get default microphone
                try:
                    source = sr.Microphone()
                except Exception as mic_error:
                    print(f"Cannot access microphone: {mic_error}")
                    print("Audio recording not available in this environment.")
                    return

            print("Listening... (speak now for up to 30 seconds)")
            # Record for a fixed duration since we can't stream with this method
            audio = self.recognizer.listen(source, timeout=5, phrase_time_limit=30)

            # Convert to raw data for processing
            raw_data = audio.get_raw_data()
            print(f"Captured {len(raw_data)} bytes of audio data")

            # Split into chunks for processing
            chunk_size = max(1, len(raw_data) // 10)  # Split into 10 chunks, ensure chunk_size > 0
            for i in range(0, len(raw_data), chunk_size):
                chunk = raw_data[i:i + chunk_size]
                if chunk:  # Only put non-empty chunks
                    self.audio_queue.put(chunk)

        except sr.WaitTimeoutError:
            print("No speech detected within timeout period")
        except Exception as e:
            print(f"Error with SpeechRecognition recording: {e}")
            import traceback
            traceback.print_exc()

    def _process_audio_queue(self):
        """Process audio chunks with intelligent sentence boundary detection"""
        buffer = []
        last_transcription_time = time.time()
        consecutive_silence_chunks = 0
        silence_threshold = 3  # Number of silent chunks before considering a pause

        while self.is_recording or not self.audio_queue.empty():
            try:
                # Collect audio chunks for processing
                start_time = time.time()
                chunk_timeout = 1.5  # Even more responsive processing

                while time.time() - start_time < chunk_timeout and (self.is_recording or not self.audio_queue.empty()):
                    if not self.audio_queue.empty():
                        data = self.audio_queue.get(timeout=0.1)
                        buffer.append(data)
                    else:
                        time.sleep(0.03)  # Very responsive sleep

                if buffer:
                    # Convert buffer to audio data
                    audio_data = b''.join(buffer)

                    # Convert to speech_recognition AudioData
                    audio = sr.AudioData(audio_data, self.sample_rate, 2)

                    try:
                        # Use enhanced transcriber for better accuracy with language specification
                        enhanced_result = self.enhanced_transcriber.transcribe_enhanced(audio_data, language='en-US')
                        text = enhanced_result.get("text", "")
                        confidence = enhanced_result.get("confidence", 0.5)

                        if text.strip():
                            # Intelligent sentence boundary detection
                            current_time = time.time()
                            time_since_last = current_time - last_transcription_time

                            # Reset silence counter when we detect speech
                            consecutive_silence_chunks = 0

                            # Check for sentence-ending patterns in the text
                            sentence_enders = ['.', '!', '?', '...']
                            question_words = ['what', 'how', 'why', 'when', 'where', 'who', 'which', 'whose']
                            text_lower = text.lower().strip()

                            # Detect if this might be a complete sentence or question
                            is_complete_sentence = (
                                any(text.endswith(ender) for ender in sentence_enders) or
                                any(text_lower.startswith(qw) for qw in question_words) or
                                len(text.split()) > 12  # Long utterances are likely complete thoughts
                            )

                            # Transcribe immediately if:
                            # 1. It's been more than 1.5 seconds (shorter pause detection)
                            # 2. Text contains sentence-ending punctuation
                            # 3. It's a question or long utterance
                            # 4. Confidence is very high (likely complete thought)
                            should_transcribe_now = (
                                time_since_last > 1.5 or
                                is_complete_sentence or
                                confidence > 0.85
                            )

                            if should_transcribe_now:
                                # This appears to be a complete thought/sentence
                                timestamp = current_time
                                transcript_entry = {
                                    "speaker": "Speaker 1",  # Placeholder - will be updated with diarization
                                    "text": text,
                                    "timestamp": timestamp,
                                    "confidence": confidence
                                }

                                self.transcript.append(transcript_entry)

                                # Call callback if set
                                if self.on_transcript_update:
                                    self.on_transcript_update(transcript_entry)

                                print(f"✅ Complete sentence (confidence: {confidence:.2f}): {text}")
                                last_transcription_time = current_time

                                # Clear buffer after successful transcription
                                buffer = []
                            else:
                                # Keep buffering - this might be part of a longer sentence
                                print(f"🔄 Buffering continuation (confidence: {confidence:.2f}): {text}")

                        else:
                            # No speech detected in this chunk
                            consecutive_silence_chunks += 1

                            # If we've had enough consecutive silence, transcribe buffered content
                            if consecutive_silence_chunks >= silence_threshold and buffer:
                                try:
                                    # Transcribe all buffered content as one complete segment
                                    buffered_audio_data = b''.join(buffer)
                                    buffered_result = self.enhanced_transcriber.transcribe_enhanced(buffered_audio_data)
                                    buffered_text = buffered_result.get("text", "")
                                    buffered_confidence = buffered_result.get("confidence", 0.5)

                                    if buffered_text.strip():
                                        timestamp = time.time()
                                        transcript_entry = {
                                            "speaker": "Speaker 1",
                                            "text": buffered_text,
                                            "timestamp": timestamp,
                                            "confidence": buffered_confidence
                                        }

                                        self.transcript.append(transcript_entry)

                                        if self.on_transcript_update:
                                            self.on_transcript_update(transcript_entry)

                                        print(f"✅ Transcribed buffered segment (confidence: {buffered_confidence:.2f}): {buffered_text}")
                                        last_transcription_time = timestamp

                                        # Clear buffer and reset silence counter
                                        buffer = []
                                        consecutive_silence_chunks = 0
                                except Exception as e:
                                    print(f"⚠️  Failed to transcribe buffered content: {e}")

                    except sr.UnknownValueError:
                        # No speech detected - increment silence counter
                        consecutive_silence_chunks += 1

                        # If we've accumulated significant silence and have buffered content, transcribe it
                        if consecutive_silence_chunks >= silence_threshold and buffer and len(buffer) > 1:
                            try:
                                buffered_audio_data = b''.join(buffer)
                                buffered_result = self.enhanced_transcriber.transcribe_enhanced(buffered_audio_data)
                                buffered_text = buffered_result.get("text", "")

                                if buffered_text.strip():
                                    timestamp = time.time()
                                    transcript_entry = {
                                        "speaker": "Speaker 1",
                                        "text": buffered_text,
                                        "timestamp": timestamp,
                                        "confidence": 0.5  # Lower confidence for silence-triggered transcription
                                    }

                                    self.transcript.append(transcript_entry)

                                    if self.on_transcript_update:
                                        self.on_transcript_update(transcript_entry)

                                    print(f"✅ Transcribed on silence (buffered): {buffered_text}")
                                    last_transcription_time = timestamp

                                    # Clear buffer and reset silence counter
                                    buffer = []
                                    consecutive_silence_chunks = 0
                            except Exception as e:
                                print(f"⚠️  Failed to transcribe buffered content: {e}")

                        elif consecutive_silence_chunks % 5 == 0:  # Log every 5 silence chunks
                            print(f"🔇 Silence detected ({consecutive_silence_chunks} consecutive chunks)")

                    except sr.RequestError as e:
                        print(f"❌ Speech recognition error: {e}")

            except queue.Empty:
                continue
            except Exception as e:
                print(f"❌ Error processing audio: {e}")
                import traceback
                traceback.print_exc()

        # Final transcription of any remaining buffered content
        if buffer and self.transcript:
            try:
                # Use enhanced transcriber for final transcription too
                final_audio_data = b''.join(buffer)
                final_result = self.enhanced_transcriber.transcribe_enhanced(final_audio_data)
                final_text = final_result.get("text", "")
                final_confidence = final_result.get("confidence", 0.4)

                if final_text.strip():
                    timestamp = time.time()
                    transcript_entry = {
                        "speaker": "Speaker 1",
                        "text": final_text,
                        "timestamp": timestamp,
                        "confidence": final_confidence
                    }

                    self.transcript.append(transcript_entry)

                    if self.on_transcript_update:
                        self.on_transcript_update(transcript_entry)

                    print(f"✅ Final transcription (confidence: {final_confidence:.2f}): {final_text}")

            except Exception as e:
                print(f"⚠️  Failed final transcription: {e}")

        print("🎵 Audio processing finished.")

    def get_current_transcript(self) -> List[Dict]:
        """Get current transcript for the active meeting"""
        return self.transcript.copy()

    def set_transcript_callback(self, callback: Callable[[Dict], None]):
        """Set callback for real-time transcript updates"""
        self.on_transcript_update = callback