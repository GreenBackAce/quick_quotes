"""
Speaker diarization module using pyannote.audio
"""

from typing import List, Dict, Tuple, Optional
import os
import torch
import torchaudio

import warnings

# Monkey patch for torchaudio < 2.1 compatibility required by speechbrain
if not hasattr(torchaudio, "list_audio_backends"):
    torchaudio.list_audio_backends = lambda: ["soundfile"]
    torchaudio.set_audio_backend = lambda x: None
    torchaudio.get_audio_backend = lambda: "soundfile"

from pyannote.audio import Pipeline
import config

class SpeakerDiarizer:
    def __init__(self):
        self.pipeline = None
        self.hf_token = config.config.HUGGINGFACE_TOKEN
        
        # Debug: Check token availability
        if self.hf_token:
            print(f"🔑 HuggingFace token found: {self.hf_token[:20]}...")
        else:
            print("❌ WARNING: No HuggingFace token found! Diarization will be disabled.")
            print(f"   Token value from config: {repr(self.hf_token)}")
        
        # Suppress specific PyTorch/PyAnnote warnings
        warnings.filterwarnings("ignore", message=".*degrees of freedom.*")
        
        if self.hf_token:
            try:
                print("🔄 Initializing pyannote.audio pipeline...")
                self.pipeline = Pipeline.from_pretrained(
                    config.config.DIARIZATION_MODEL,
                    token=self.hf_token
                )
                
                # Use GPU if available
                if torch.cuda.is_available():
                    self.pipeline.to(torch.device("cuda"))
                    print("✅ Speaker diarization initialized on GPU")
                else:
                    print("✅ Speaker diarization initialized on CPU")
                
                # Tune parameters to reduce flickering
                try:
                    # Set minimum duration for speaker turns and silence
                    # This helps avoid "flickering" where short noises are detected as speaker changes
                    params = {
                        "segmentation": {
                            "min_duration_off": 0.5,
                            # "min_duration_on": 0.5, # Not supported in this version
                        }
                    }
                    self.pipeline.instantiate(params)
                    print("✅ Applied custom diarization parameters (min_duration_off = 0.5s)")
                except Exception as e:
                    print(f"⚠️ Could not apply custom parameters: {e}")
            except Exception as e:
                print(f"❌ Failed to initialize speaker diarization: {e}")
                import traceback
                traceback.print_exc()
        else:
            print("⚠️  Skipping speaker diarization (no HuggingFace token)")

    def diarize_audio_file(self, audio_file_path: str) -> List[Tuple[float, float, str]]:
        """
        Perform speaker diarization on an audio file
        
        Args:
            audio_file_path: Path to the audio file
            
        Returns:
            List of tuples: (start_time, end_time, speaker_id)
        """
        if not self.pipeline:
            return []

        try:
            print(f"🔄 Running diarization on {audio_file_path}...")
            # Run diarization
            diarization = self.pipeline(audio_file_path)
            
            # Handle pyannote 4.0 output
            if hasattr(diarization, "speaker_diarization"):
                diarization = diarization.speaker_diarization

            # Convert to list of tuples
            segments = []
            for turn, _, speaker in diarization.itertracks(yield_label=True):
                segments.append((turn.start, turn.end, speaker))
            
            print(f"✅ Diarization complete: found {len(segments)} segments")
            return segments

        except Exception as e:
            print(f"❌ Error during diarization: {e}")
            return []

    def diarize_transcript(self, transcript: List[Dict], audio_file_path: str = None, diarization_segments: List[Tuple[float, float, str]] = None) -> List[Dict]:
        """
        Apply speaker diarization to an existing transcript
        
        Args:
            transcript: List of transcript entries with timestamps
            audio_file_path: Optional path to audio file for diarization (if segments not provided)
            diarization_segments: Optional pre-calculated diarization segments
            
        Returns:
            Updated transcript with speaker labels
        """
        if not transcript:
            return []

        # If we have pre-calculated segments, use them
        segments = diarization_segments

        # If not, try to calculate them from audio file
        if not segments and audio_file_path and self.pipeline:
            try:
                segments = self.diarize_audio_file(audio_file_path)
            except Exception as e:
                print(f"⚠️  Diarization failed inside diarize_transcript: {e}")
        
        # If still no segments, fallback to heuristics
        if not segments:
            return self._heuristic_diarization(transcript)

        try:
            # Check if we have word-level timestamps
            has_words = any("words" in entry and entry["words"] for entry in transcript)
            
            if has_words:
                print("📝 Using word-level timestamps for precise diarization...")
                # Flatten all words
                all_words = []
                for entry in transcript:
                    if "words" in entry and entry["words"]:
                        all_words.extend(entry["words"])
                    else:
                        # Fallback for segments without words (create a dummy word)
                        all_words.append({
                            "word": entry["text"],
                            "start": entry["start"],
                            "end": entry["end"],
                            "probability": entry.get("confidence", 0.0)
                        })
                
                # Debug: Print first few segments and words
                print(f"   🔍 DEBUG: Total Diarization Segments: {len(segments)}")
                if segments:
                    print(f"   🔍 DEBUG: First 5 Diarization Segments:")
                    for i, seg in enumerate(segments[:5]):
                        if isinstance(seg, (list, tuple)) and len(seg) == 3:
                            print(f"      [{i}] {seg[2]}: {seg[0]:.2f}-{seg[1]:.2f}")
                    
                    # Show all SPEAKER_01 segments
                    speaker1_segs = [seg for seg in segments if isinstance(seg, (list, tuple)) and len(seg) == 3 and seg[2] == 'SPEAKER_01']
                    print(f"   🔍 DEBUG: All SPEAKER_01 segments ({len(speaker1_segs)} total):")
                    for seg in speaker1_segs[:10]:  # Show first 10
                        print(f"      SPEAKER_01: {seg[0]:.2f}-{seg[1]:.2f}")
                
                print(f"   🔍 DEBUG: Total Words: {len(all_words)}")
                if all_words:
                    print(f"   🔍 DEBUG: First 5 Words:")
                    for i, w in enumerate(all_words[:5]):
                        print(f"      [{i}] '{w['word']}': {w['start']:.2f}-{w['end']:.2f}")

                # Assign speaker to each word
                word_speakers = []
                for word in all_words:
                    w_start = word["start"]
                    w_end = word["end"]
                    w_center = (w_start + w_end) / 2
                    
                    # Find speaker with max overlap
                    speaker_overlaps = {}
                    
                    for item in segments:
                        if isinstance(item, (list, tuple)) and len(item) == 3:
                            seg_start, seg_end, speaker = item
                        else:
                            continue

                        overlap_start = max(w_start, seg_start)
                        overlap_end = min(w_end, seg_end)
                        overlap_duration = max(0, overlap_end - overlap_start)
                        if overlap_duration > 0:
                            speaker_overlaps[speaker] = speaker_overlaps.get(speaker, 0) + overlap_duration
                    
                    best_speaker = "Unknown"
                    if speaker_overlaps:
                        best_speaker = max(speaker_overlaps.items(), key=lambda x: x[1])[0]
                    else:
                        # No overlap - word falls in gap between segments
                        # Find nearest segment by distance to word center
                        min_distance = float('inf')
                        nearest_speaker = "Unknown"
                        
                        for item in segments:
                            if isinstance(item, (list, tuple)) and len(item) == 3:
                                seg_start, seg_end, speaker = item
                                seg_center = (seg_start + seg_end) / 2
                                distance = abs(w_center - seg_center)
                                if distance < min_distance:
                                    min_distance = distance
                                    nearest_speaker = speaker
                        
                        best_speaker = nearest_speaker
                    
                    word_speakers.append({
                        "word": word["word"],
                        "start": w_start,
                        "end": w_end,
                        "speaker": best_speaker,
                        "probability": word.get("probability", 0.0)
                    })
                
                print(f"   🔍 Created {len(word_speakers)} word-speaker assignments")
                if word_speakers:
                    speaker_counts = {}
                    for w in word_speakers:
                        speaker_counts[w["speaker"]] = speaker_counts.get(w["speaker"], 0) + 1
                    print(f"   🔍 Speaker distribution: {speaker_counts}")
                
                # Hybrid approach: Use Whisper's sentence boundaries but split on speaker changes
                new_transcript = []
                
                for entry in transcript:
                    entry_start = entry.get("start", 0)
                    entry_end = entry.get("end", entry_start + 1)
                    
                    # Find all words that overlap with this Whisper segment
                    segment_words = [w for w in word_speakers if w["end"] > entry_start and w["start"] < entry_end]
                    
                    if not segment_words:
                        # No words, keep original with Unknown
                        new_entry = entry.copy()
                        new_entry["speaker"] = "Unknown"
                        new_transcript.append(new_entry)
                        continue
                    
                    # Check if there's a speaker change within this segment
                    speakers_in_segment = list(set(w["speaker"] for w in segment_words))
                    
                    if len(speakers_in_segment) == 1:
                        # Single speaker, use the whole segment
                        new_entry = entry.copy()
                        new_entry["speaker"] = speakers_in_segment[0]
                        new_transcript.append(new_entry)
                    else:
                        # Multiple speakers - split on speaker changes
                        current_speaker = segment_words[0]["speaker"]
                        current_words = [segment_words[0]]
                        
                        for i in range(1, len(segment_words)):
                            word = segment_words[i]
                            
                            if word["speaker"] != current_speaker:
                                # Speaker changed - create sub-segment
                                text = "".join([w["word"] for w in current_words])
                                new_transcript.append({
                                    "speaker": current_speaker,
                                    "start": current_words[0]["start"],
                                    "end": current_words[-1]["end"],
                                    "text": text.strip(),
                                    "words": current_words
                                })
                                
                                # Start new sub-segment
                                current_speaker = word["speaker"]
                                current_words = [word]
                            else:
                                current_words.append(word)
                        
                        # Add final sub-segment
                        if current_words:
                            text = "".join([w["word"] for w in current_words])
                            new_transcript.append({
                                "speaker": current_speaker,
                                "start": current_words[0]["start"],
                                "end": current_words[-1]["end"],
                                "text": text.strip(),
                                "words": current_words
                            })
                
                print(f"   🔍 Created {len(new_transcript)} segments (hybrid: Whisper boundaries + speaker splits)")
                return new_transcript

            else:
                # Fallback to segment-level alignment (Legacy logic)
                print("⚠️ No word timestamps found, falling back to segment-level alignment")
                updated_transcript = []
                for entry in transcript:
                    entry_start = entry.get("start", 0)
                    entry_end = entry.get("end", entry_start + entry.get("chunk_duration", 0))
                    
                    speaker_overlaps = {}
                    for seg_start, seg_end, speaker in segments:
                        overlap_start = max(entry_start, seg_start)
                        overlap_end = min(entry_end, seg_end)
                        overlap_duration = max(0, overlap_end - overlap_start)
                        if overlap_duration > 0:
                            speaker_overlaps[speaker] = speaker_overlaps.get(speaker, 0) + overlap_duration
                    
                    best_speaker = "Unknown"
                    if speaker_overlaps:
                        best_speaker = max(speaker_overlaps.items(), key=lambda x: x[1])[0]
                    
                    updated_entry = entry.copy()
                    updated_entry["speaker"] = best_speaker
                    updated_transcript.append(updated_entry)
                    
                return updated_transcript

        except Exception as e:
            print(f"❌ Error applying diarization to transcript: {e}")
            return self._heuristic_diarization(transcript)

    def _heuristic_diarization(self, transcript: List[Dict]) -> List[Dict]:
        """
        Simple heuristic diarization based on time gaps and text analysis
        """
        if not transcript:
            return transcript

        updated_transcript = []
        current_speaker = "Speaker 1"
        last_end_time = 0
        
        for entry in transcript:
            start_time = entry.get("start_time", 0)
            
            # If there's a significant time gap, switch speakers
            if start_time - last_end_time > 2.0:  # 2 seconds gap
                current_speaker = "Speaker 2" if current_speaker == "Speaker 1" else "Speaker 1"
            
            updated_entry = entry.copy()
            updated_entry["speaker"] = current_speaker
            updated_transcript.append(updated_entry)
            
            last_end_time = start_time + entry.get("chunk_duration", 0)

        return updated_transcript