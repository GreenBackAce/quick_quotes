"""
FastAPI backend for Quick Quotes Quill - AI Meeting Notes Taker
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import asyncio
import uuid
from datetime import datetime
import os
import tempfile
import warnings

# Suppress pkg_resources deprecation warning from webrtcvad
warnings.filterwarnings("ignore", category=UserWarning, module="webrtcvad")

from .audio_processor import AudioProcessor
from .database import DatabaseManager
from .diarizer import SpeakerDiarizer
from .intelligence import MeetingIntelligence
import config

app = FastAPI(title="Quick Quotes Quill API", version="1.0.0")

# Add CORS middleware for Streamlit frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8501", "http://localhost:3000"],  # Streamlit and Next.js ports
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
) 

# Lazy-loaded global instances (only initialized when needed to speed up startup)
_audio_processor = None
_diarizer = None
_meeting_intelligence = None

def get_audio_processor():
    """Lazy-load audio processor (for live recording only)"""
    global _audio_processor
    if _audio_processor is None:
        from .audio_processor import AudioProcessor
        print("⏳ Initializing AudioProcessor for live recording...")
        _audio_processor = AudioProcessor()
    return _audio_processor

def get_diarizer():
    """Lazy-load diarizer (for local fallback only)"""
    global _diarizer
    if _diarizer is None:
        from .diarizer import SpeakerDiarizer
        print("⏳ Initializing SpeakerDiarizer for local processing...")
        _diarizer = SpeakerDiarizer()
    return _diarizer

def get_meeting_intelligence():
    """Lazy-load meeting intelligence"""
    global _meeting_intelligence
    if _meeting_intelligence is None:
        from .intelligence import MeetingIntelligence
        print("⏳ Initializing MeetingIntelligence...")
        _meeting_intelligence = MeetingIntelligence()
    return _meeting_intelligence

# Always initialize database manager (lightweight)
db_manager = DatabaseManager()

# Simple in-memory progress tracker
# Format: {meeting_id: {"progress": int, "status": str, "error": str}}
progress_tracker = {}

class MeetingRequest(BaseModel):
    meeting_title: Optional[str] = "Untitled Meeting"

class ProgressResponse(BaseModel):
    meeting_id: str
    progress: int
    status: str
    error: Optional[str] = None

class MeetingResponse(BaseModel):
    meeting_id: str
    status: str
    message: str

class UploadResponse(BaseModel):
    meeting_id: str
    status: str
    message: str
    filename: str

class TranscriptResponse(BaseModel):
    meeting_id: str
    transcript: List[dict]
    summary: Optional[str] = None

class ChatRequest(BaseModel):
    question: str

class ChatResponse(BaseModel):
    answer: str

class AnalyticsResponse(BaseModel):
    talk_time: dict
    sentiment: dict

@app.on_event("startup")
async def startup_event():
    """Initialize database and check dependencies on startup"""
    try:
        db_manager.init_db()
        print("Database initialized successfully")
    except Exception as e:
        print(f"Warning: Database initialization failed: {e}")

    # Check configuration
    warnings = config.Config.validate()
    for warning in warnings:
        print(f"Configuration Warning: {warning}")

@app.post("/meetings/start", response_model=MeetingResponse)
async def start_meeting(request: MeetingRequest, background_tasks: BackgroundTasks):
    """Start a new meeting recording session"""
    try:
        meeting_id = str(uuid.uuid4())
        meeting_title = request.meeting_title or f"Meeting {datetime.now().strftime('%Y-%m-%d %H:%M')}"

        # Create meeting record in database
        db_manager.create_meeting(meeting_id, meeting_title)

        # Start audio processing in background
        background_tasks.add_task(get_audio_processor().start_recording, meeting_id)

        return MeetingResponse(
            meeting_id=meeting_id,
            status="started",
            message=f"Meeting '{meeting_title}' started successfully"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start meeting: {str(e)}")

@app.post("/meetings/{meeting_id}/stop", response_model=MeetingResponse)
async def stop_meeting(meeting_id: str):
    """Stop a meeting recording session and generate summary"""
    try:
        # Stop recording
        transcript = get_audio_processor().stop_recording(meeting_id)

        if transcript:
            # Apply speaker diarization
            try:
                transcript = get_diarizer().diarize_transcript(transcript)
            except Exception as e:
                print(f"Warning: Speaker diarization failed: {e}")

            # Save transcript to database
            db_manager.save_transcript(meeting_id, transcript)

            # Generate summary using LLM
            try:
                from .summarizer import Summarizer
                summarizer = Summarizer()
                summary = summarizer.generate_summary(transcript)

                # Save summary to database
                db_manager.save_summary(meeting_id, summary)

                return MeetingResponse(
                    meeting_id=meeting_id,
                    status="completed",
                    message="Meeting stopped, diarized, and summary generated"
                )
            except Exception as e:
                print(f"Error generating summary: {e}")
                return MeetingResponse(
                    meeting_id=meeting_id,
                    status="completed",
                    message="Meeting stopped and diarized (summary generation failed)"
                )
        else:
            return MeetingResponse(
                meeting_id=meeting_id,
                status="stopped",
                message="Meeting stopped (no transcript available)"
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to stop meeting: {str(e)}")

@app.get("/meetings/{meeting_id}/transcript", response_model=TranscriptResponse)
async def get_transcript(meeting_id: str):
    """Get transcript and summary for a meeting"""
    try:
        transcript = db_manager.get_transcript(meeting_id)
        summary = db_manager.get_summary(meeting_id)

        if not transcript:
            raise HTTPException(status_code=404, detail="Meeting not found or no transcript available")

        return TranscriptResponse(
            meeting_id=meeting_id,
            transcript=transcript,
            summary=summary
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve transcript: {str(e)}")

@app.get("/meetings/{meeting_id}/progress", response_model=ProgressResponse)
async def get_progress(meeting_id: str):
    """Get the processing progress of a meeting"""
    progress_data = progress_tracker.get(meeting_id)
    
    if not progress_data:
        # Check if meeting exists in DB (completed)
        try:
            transcript = db_manager.get_transcript(meeting_id)
            if transcript:
                return ProgressResponse(
                    meeting_id=meeting_id,
                    progress=100,
                    status="Completed",
                    error=None
                )
        except:
            pass
            
        # If not in tracker and not in DB, return 0 or not found
        # For now, return 0 to avoid 404s during initial upload lag
        return ProgressResponse(
            meeting_id=meeting_id,
            progress=0,
            status="Waiting...",
            error=None
        )
        
    return ProgressResponse(
        meeting_id=meeting_id,
        progress=progress_data.get("progress", 0),
        status=progress_data.get("status", "Processing"),
        error=progress_data.get("error")
    )

@app.get("/meetings")
async def list_meetings():
    """List all meetings"""
    try:
        meetings = db_manager.list_meetings()
        return {"meetings": meetings}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list meetings: {str(e)}")

@app.delete("/meetings/{meeting_id}")
async def delete_meeting(meeting_id: str):
    """Delete a meeting and its data"""
    try:
        success = db_manager.delete_meeting(meeting_id)
        if success:
            return {"message": f"Meeting {meeting_id} deleted successfully"}
        else:
            raise HTTPException(status_code=404, detail="Meeting not found")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete meeting: {str(e)}")

@app.post("/meetings/upload", response_model=UploadResponse)
async def upload_meeting_audio(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    meeting_title: Optional[str] = None
):
    """Upload an audio file for processing and create a meeting record"""
    try:
        # Validate file type
        allowed_extensions = {'.wav', '.mp3', '.m4a', '.flac', '.ogg'}
        file_extension = os.path.splitext(file.filename.lower())[1]

        if file_extension not in allowed_extensions:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type. Allowed: {', '.join(allowed_extensions)}"
            )

        # Create meeting record
        meeting_id = str(uuid.uuid4())
        title = meeting_title or f"Uploaded Meeting - {file.filename}"

        if not db_manager.create_meeting(meeting_id, title):
            raise HTTPException(status_code=500, detail="Failed to create meeting record")

        # Save uploaded file temporarily
        temp_dir = tempfile.mkdtemp()
        temp_file_path = os.path.join(temp_dir, f"{meeting_id}_{file.filename}")

        try:
            # Save uploaded file
            with open(temp_file_path, "wb") as buffer:
                content = await file.read()
                buffer.write(content)

            # Process the audio file in background
            background_tasks.add_task(
                process_uploaded_audio,
                meeting_id,
                temp_file_path,
                temp_dir
            )

            return UploadResponse(
                meeting_id=meeting_id,
                status="processing",
                message=f"Audio file '{file.filename}' uploaded successfully. Processing started.",
                filename=file.filename
            )

        except Exception as e:
            # Clean up on error
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
            if os.path.exists(temp_dir):
                os.rmdir(temp_dir)
            raise HTTPException(status_code=500, detail=f"Failed to save uploaded file: {str(e)}")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

import traceback

async def process_uploaded_audio(meeting_id: str, audio_file_path: str, temp_dir: str):
    """Process uploaded audio file for transcription and summarization"""
    try:
        print(f"🎵 Processing uploaded audio file: {audio_file_path}")
        
        # Initialize progress
        progress_tracker[meeting_id] = {"progress": 0, "status": "Starting processing...", "error": None}

        # Import here to avoid circular imports
        from .audio_processor import AudioProcessor
        from .summarizer import Summarizer
        from .enhanced_transcriber import EnhancedTranscriber

        # Initialize processors
        audio_processor = AudioProcessor()
        summarizer = Summarizer()
        enhanced_transcriber = EnhancedTranscriber()

        # For uploaded files, use enhanced transcription with preprocessing
        from pydub import AudioSegment
        import numpy as np
        import io

        # Try to process the audio file
        transcript_entries = []

        try:
            # Check if we should use Remote GPU
            if config.config.USE_REMOTE_GPU:
                try:
                    print("☁️  Using Remote GPU for processing...")
                    progress_tracker[meeting_id] = {"progress": 20, "status": "Uploading to Cloud GPU...", "error": None}
                    
                    # Import modal client wrapper
                    from .modal_client import process_remote_audio
                    
                    # Run remote processing in thread
                    print("🚀 Sending to Modal...")
                    transcript_entries = await asyncio.to_thread(process_remote_audio, audio_file_path)
                    
                    if not transcript_entries:
                        raise Exception("Remote processing returned empty transcript")
                    
                    print(f"✅ Remote processing complete! ({len(transcript_entries)} segments)")
                    progress_tracker[meeting_id] = {"progress": 80, "status": "Cloud processing complete. Saving...", "error": None}
                    
                except Exception as e:
                    print(f"⚠️  Remote GPU failed: {e}")
                    print("🔄 Falling back to local processing...")
                    # Fallback to local processing logic (continue below)
                    transcript_entries = [] # Reset to trigger local fallback
            
            # Local Processing (Fallback or Default)
            if not transcript_entries:
                # Load and preprocess the audio file
                progress_tracker[meeting_id] = {"progress": 10, "status": "Converting audio format (Local)...", "error": None}
                try:
                    audio = AudioSegment.from_file(audio_file_path)
                    duration_ms = len(audio)
                    duration_sec = duration_ms / 1000

                    print("🎵 Processing uploaded audio file locally...")
                    print(f"📊 Audio duration: {duration_sec:.1f} seconds ({duration_sec/60:.1f} minutes)")

                    # Convert to WAV format for processing (required for PyAnnote and optimized for Whisper)
                    wav_path = audio_file_path.replace(os.path.splitext(audio_file_path)[1], '.wav')
                    audio.export(wav_path, format='wav', parameters=["-ac", "1", "-ar", "16000"])  # Mono, 16kHz
                    print(f"✅ Converted and optimized audio to WAV: {wav_path}")
                    progress_tracker[meeting_id] = {"progress": 15, "status": "Audio converted. Starting local analysis...", "error": None}

                except Exception as e:
                    print(f"⚠️  Audio conversion failed: {e}, trying direct WAV processing")
                    if audio_file_path.lower().endswith('.wav'):
                        wav_path = audio_file_path
                    else:
                        print("❌ Cannot process non-WAV files without ffmpeg/pydub")
                        progress_tracker[meeting_id] = {"progress": 0, "status": "Failed", "error": "Audio conversion failed"}
                        return

                # Run Diarization and Transcription in PARALLEL
                print("🚀 Starting parallel processing (Diarization + Transcription)...")
                progress_tracker[meeting_id] = {"progress": 20, "status": "Analyzing audio (Local Diarization & Transcription)...", "error": None}
                
                # Define wrapper functions for async execution
                def run_diarization():
                    print("👥 Starting speaker diarization...")
                    try:
                        return get_diarizer().diarize_audio_file(wav_path)
                    except Exception as e:
                        print(f"⚠️  Diarization failed: {e}")
                        return []

                def run_transcription():
                    print("📝 Starting transcription...")
                    try:
                        return enhanced_transcriber.transcribe_file(wav_path)
                    except Exception as e:
                        print(f"❌ Transcription failed: {e}")
                        return {"segments": []}

                # Execute sequentially to avoid CPU thrashing
                diarization_segments = await asyncio.to_thread(run_diarization)
                raw_transcript_segments = await asyncio.to_thread(run_transcription)
                
                print(f"✅ Parallel processing complete.")
                print(f"   - Diarization: {len(diarization_segments)} segments")
                print(f"   - Transcription: {len(raw_transcript_segments.get('segments', []))} segments")
                
                progress_tracker[meeting_id] = {"progress": 80, "status": "Analysis complete. Merging results...", "error": None}

                # Merge Transcription and Diarization
                segments_list = raw_transcript_segments.get("segments", [])
                transcript_entries = []

                if segments_list:
                    print("🔄 Merging transcription and diarization...")
                    progress_tracker[meeting_id] = {"progress": 85, "status": "Assigning speakers to text...", "error": None}
                    
                    # Create initial transcript entries
                    for segment in segments_list:
                        start_sec = segment.get("start", 0)
                        end_sec = segment.get("end", 0)
                        text = segment.get("text", "")
                        
                        # Format relative time as HH:MM:SS
                        m, s = divmod(int(start_sec), 60)
                        h, m = divmod(m, 60)
                        relative_time = f"{h:02d}:{m:02d}:{s:02d}"
                        
                        transcript_entries.append({
                            "text": text,
                            "timestamp": datetime.now().timestamp() + start_sec, # Keep absolute for DB compatibility
                            "start_time": start_sec, # Relative seconds for diarization
                            "chunk_duration": end_sec - start_sec,
                            "relative_time": relative_time, # Readable time for UI
                            "speaker": "Unknown", # Will be filled by diarization
                            "words": segment.get("words", []) # Pass word-level data for diarization
                        })
                    
                    # Apply diarization
                    if diarization_segments:
                        transcript_entries = get_diarizer().diarize_transcript(transcript_entries, diarization_segments=diarization_segments)
                    else:
                        # Fallback if diarization failed entirely
                        transcript_entries = get_diarizer().diarize_transcript(transcript_entries) # This will apply heuristic diarization

            # 5. Save to Database
            if transcript_entries:
                progress_tracker[meeting_id] = {"progress": 90, "status": "Saving results and generating summary...", "error": None}
                db_manager.save_transcript(meeting_id, transcript_entries)
            
                # 6. Generate Summary
                try:
                    full_text = "\n".join([f"{t.get('speaker', 'Unknown')}: {t['text']}" for t in transcript_entries])
                    summary = summarizer.summarize_text(full_text)
                    db_manager.save_summary(meeting_id, summary)
                    print(f"✅ Processed uploaded meeting {meeting_id}: {len(transcript_entries)} segments, summary generated")
                except Exception as e:
                    error_msg = str(e)
                    if "429" in error_msg:
                        print("⚠️  Quota exceeded for summarization. Skipping summary.")
                        db_manager.save_summary(meeting_id, "Summary unavailable due to API quota limits. Please try again later.")
                    else:
                        print(f"❌ Error generating summary: {e}")
                        db_manager.save_summary(meeting_id, f"Error generating summary: {e}")
                
                progress_tracker[meeting_id] = {"progress": 100, "status": "Completed", "error": None}
            else:
                print("⚠️  No transcript generated, skipping summary.")
                db_manager.save_summary(meeting_id, "No transcript generated, so no summary available.")
                progress_tracker[meeting_id] = {"progress": 100, "status": "Completed (No transcript)", "error": None}
                
        except Exception as e:
            print(f"❌ Error during transcription/diarization: {e}")
            traceback.print_exc()
            progress_tracker[meeting_id] = {"progress": 0, "status": "Failed", "error": str(e)}
        finally:
            # Cleanup temp wav if it was created and is different from original
            if 'wav_path' in locals() and wav_path and os.path.exists(wav_path) and wav_path != audio_file_path:
                try:
                    os.remove(wav_path)
                    print("🧹 Cleaned up temporary WAV file")
                except Exception as e:
                    print(f"⚠️  Failed to clean up temporary WAV file: {e}")

        # Clean up original uploaded file and temp directory
        try:
            if os.path.exists(audio_file_path):
                os.unlink(audio_file_path)
            if os.path.exists(temp_dir):
                os.rmdir(temp_dir)
        except Exception as e:
            print(f"Warning: Failed to clean up temp files: {e}")

    except Exception as e:
        print(f"❌ Error processing uploaded audio: {e}")

@app.get("/meetings/{meeting_id}/export")
async def export_meeting(meeting_id: str):
    """Export meeting transcript and summary as formatted text"""
    try:
        transcript = db_manager.get_transcript(meeting_id)
        summary = db_manager.get_summary(meeting_id)

        # Allow export even if no transcript, as long as meeting exists
        # Get meeting info
        meetings = db_manager.list_meetings()
        meeting_info = next((m for m in meetings if m['id'] == meeting_id), None)

        if not meeting_info:
            raise HTTPException(status_code=404, detail="Meeting not found")

        # Format the export
        export_content = f"""MEETING NOTES EXPORT
{'='*50}

Meeting Title: {meeting_info['title']}
Date: {meeting_info['created_at']}
Meeting ID: {meeting_id}

{'='*50}
"""

        # Import datetime at function scope
        from datetime import datetime

        if transcript:
            export_content += f"""TRANSCRIPT
{'='*50}

"""
            for i, entry in enumerate(transcript, 1):
                speaker = entry.get("speaker", "Unknown")
                text = entry.get("text", "").strip()
                timestamp = entry.get("timestamp", 0)

                # Format timestamp
                dt = datetime.fromtimestamp(timestamp)
                time_str = dt.strftime("%H:%M:%S")

                export_content += f"[{time_str}] {speaker}: {text}\n\n"
        else:
            export_content += f"""TRANSCRIPT
{'='*50}

No transcript available for this meeting.

"""

        if summary:
            export_content += f"""{'='*50}
AI-GENERATED SUMMARY
{'='*50}

{summary}

"""

        export_content += f"""{'='*50}
Export generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Total segments: {len(transcript) if transcript else 0}
Has AI Summary: {'Yes' if summary else 'No'}
{'='*50}
"""

        return {
            "meeting_id": meeting_id,
            "title": meeting_info['title'],
            "content": export_content,
            "filename": f"meeting_{meeting_info['title'].replace(' ', '_')}_{meeting_id[:8]}.txt"
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to export meeting: {str(e)}")

@app.post("/meetings/{meeting_id}/chat", response_model=ChatResponse)
async def chat_with_meeting(meeting_id: str, request: ChatRequest):
    """Ask a question about the meeting"""
    try:
        transcript = db_manager.get_transcript(meeting_id)
        if not transcript:
            raise HTTPException(status_code=404, detail="Meeting transcript not found")
            
        answer = get_meeting_intelligence().chat_with_meeting(transcript, request.question)
        return {"answer": answer}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat failed: {str(e)}")

@app.get("/meetings/{meeting_id}/analytics", response_model=AnalyticsResponse)
async def get_meeting_analytics(meeting_id: str):
    """Get analytics for the meeting"""
    try:
        transcript = db_manager.get_transcript(meeting_id)
        if not transcript:
            raise HTTPException(status_code=404, detail="Meeting transcript not found")
            
        analytics = get_meeting_intelligence().analyze_meeting(transcript)
        return analytics
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analytics failed: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=config.config.BACKEND_HOST, port=config.config.BACKEND_PORT)