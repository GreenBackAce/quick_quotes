"""
Streamlit frontend for Quick Quotes Quill - AI Meeting Notes Taker
"""

import streamlit as st
import requests
import time
from typing import List, Dict, Optional
import json

# Backend API configuration
BACKEND_URL = "http://localhost:8000"

st.set_page_config(
    page_title="Quick Quotes Quill",
    page_icon="📝",
    layout="wide"
)

st.title("📝 Quick Quotes Quill")
st.subheader("AI-Powered Meeting Notes Taker")

# Initialize session state
if "recording" not in st.session_state:
    st.session_state.recording = False
if "current_meeting_id" not in st.session_state:
    st.session_state.current_meeting_id = None
if "transcript" not in st.session_state:
    st.session_state.transcript = []
if "summary" not in st.session_state:
    st.session_state.summary = None

def start_meeting(meeting_title: str) -> Optional[str]:
    """Start a new meeting recording"""
    try:
        response = requests.post(
            f"{BACKEND_URL}/meetings/start",
            json={"meeting_title": meeting_title}
        )

        if response.status_code == 200:
            data = response.json()
            return data["meeting_id"]
        else:
            st.error(f"Failed to start meeting: {response.text}")
            return None
    except Exception as e:
        st.error(f"Error connecting to backend: {e}")
        return None

def stop_meeting(meeting_id: str) -> bool:
    """Stop meeting recording and get results"""
    try:
        response = requests.post(f"{BACKEND_URL}/meetings/{meeting_id}/stop")

        if response.status_code == 200:
            return True
        else:
            st.error(f"Failed to stop meeting: {response.text}")
            return False
    except Exception as e:
        st.error(f"Error connecting to backend: {e}")
        return False

def get_meeting_data(meeting_id: str) -> tuple:
    """Get transcript and summary for a meeting"""
    try:
        response = requests.get(f"{BACKEND_URL}/meetings/{meeting_id}/transcript")

        if response.status_code == 200:
            data = response.json()
            return data.get("transcript", []), data.get("summary")
        else:
            return [], None
    except Exception as e:
        st.error(f"Error retrieving meeting data: {e}")
        return [], None

def delete_meeting(meeting_id: str) -> bool:
    """Delete a meeting from the database"""
    try:
        response = requests.delete(f"{BACKEND_URL}/meetings/{meeting_id}")

        if response.status_code == 200:
            return True
        else:
            return False
    except Exception as e:
        st.error(f"Error deleting meeting: {e}")
        return False

def export_meeting(meeting_id: str) -> tuple:
    """Export meeting data for download"""
    try:
        response = requests.get(f"{BACKEND_URL}/meetings/{meeting_id}/export")

        if response.status_code == 200:
            data = response.json()
            return data.get("content", ""), data.get("filename", "meeting.txt")
        else:
            return None, None
    except Exception as e:
        st.error(f"Error exporting meeting: {e}")
        return None, None

def list_meetings():
    """Get list of all meetings"""
    try:
        response = requests.get(f"{BACKEND_URL}/meetings")

        if response.status_code == 200:
            return response.json().get("meetings", [])
        else:
            return []
    except Exception:
        return []

def chat_with_meeting(meeting_id: str, question: str) -> str:
    """Ask a question about the meeting"""
    try:
        response = requests.post(
            f"{BACKEND_URL}/meetings/{meeting_id}/chat",
            json={"question": question}
        )
        if response.status_code == 200:
            return response.json().get("answer", "No answer received.")
        else:
            return f"Error: {response.text}"
    except Exception as e:
        return f"Connection error: {e}"

def get_analytics(meeting_id: str) -> dict:
    """Get analytics for the meeting"""
    try:
        response = requests.get(f"{BACKEND_URL}/meetings/{meeting_id}/analytics")
        if response.status_code == 200:
            return response.json()
        else:
            return {}
    except Exception:
        return {}

# File upload section
st.header("📤 Upload Audio File")
with st.expander("Upload Existing Meeting Recording", expanded=False):
    uploaded_file = st.file_uploader(
        "Choose an audio file",
        type=['wav', 'mp3', 'm4a', 'flac', 'ogg'],
        help="Upload a meeting recording to transcribe and summarize"
    )

    upload_title = st.text_input(
        "Meeting Title (optional)",
        value=f"Uploaded Meeting {time.strftime('%Y-%m-%d %H:%M')}",
        help="Custom title for the uploaded meeting"
    )

    if uploaded_file is not None:
        # Check file size (Google Speech Recognition has limits)
        file_size_mb = len(uploaded_file.getvalue()) / (1024 * 1024)
        file_ext = uploaded_file.name.lower().split('.')[-1]

        # Remove size limit for WAV files
        if file_ext == 'wav':
            max_size_mb = float('inf')  # No limit for WAV files
        else:
            max_size_mb = 500  # Allow large files since we chunk them

        if file_size_mb > max_size_mb:
            st.error(f"❌ File too large ({file_size_mb:.1f}MB). Maximum size is {max_size_mb}MB.")
            st.info("💡 Try compressing the audio or splitting it into smaller files.")
        else:
            st.audio(uploaded_file, format=f"audio/{uploaded_file.type.split('/')[-1]}")
            st.info(f"📁 File size: {file_size_mb:.1f}MB")

            # Estimate processing time
            estimated_chunks = max(1, int((file_size_mb * 1024 * 1024) / (16000 * 2 * 45)))  # Rough estimate
            estimated_time = estimated_chunks * 3  # ~3 seconds per chunk for API calls
            st.info(f"⏱️ Estimated processing time: ~{estimated_time//60}min {estimated_time%60}s ({estimated_chunks} chunks)")

            # Check if it's a supported format
            file_ext = uploaded_file.name.lower().split('.')[-1]
            if file_ext not in ['wav']:
                st.warning("⚠️ Only WAV files are fully supported. MP3/M4A files need conversion to WAV first.")
                st.info("💡 Convert with: `ffmpeg -i input.mp3 output.wav`")

            if st.button("🚀 Process Uploaded Audio", type="primary"):
                with st.spinner("Uploading and processing audio file..."):
                    # Prepare file for upload
                    files = {"file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)}
                    data = {"meeting_title": upload_title}

                    try:
                        response = requests.post(
                            f"{BACKEND_URL}/meetings/upload",
                            files=files,
                            data=data,
                            timeout=300  # 5 minute timeout for large files
                        )

                        if response.status_code == 200:
                            result = response.json()
                            st.success(f"✅ {result['message']}")
                            st.success(f"✅ {result['message']}")
                            
                            # Progress Monitoring
                            progress_bar = st.progress(0)
                            status_text = st.empty()
                            
                            meeting_id = result['meeting_id']
                            
                            while True:
                                try:
                                    prog_response = requests.get(f"{BACKEND_URL}/meetings/{meeting_id}/progress")
                                    if prog_response.status_code == 200:
                                        prog_data = prog_response.json()
                                        progress = prog_data.get("progress", 0)
                                        status = prog_data.get("status", "Processing...")
                                        
                                        progress_bar.progress(progress / 100)
                                        status_text.text(f"⏳ {status}")
                                        
                                        if progress >= 100:
                                            status_text.success("✅ Processing Complete!")
                                            time.sleep(1)
                                            break
                                        
                                        if prog_data.get("error"):
                                            st.error(f"❌ Error: {prog_data['error']}")
                                            break
                                            
                                    time.sleep(1)
                                except Exception as e:
                                    st.error(f"Connection error: {e}")
                                    break
                            
                            st.rerun()
                        else:
                            st.error(f"❌ Upload failed: {response.text}")

                    except requests.exceptions.Timeout:
                        st.error("❌ Upload timed out. Try a smaller file.")
                    except Exception as e:
                        st.error(f"❌ Error uploading file: {e}")

# Main interface
col1, col2 = st.columns([1, 2])

with col1:
    st.header("Meeting Control")

    # Meeting title input
    meeting_title = st.text_input("Meeting Title", value=f"Meeting {time.strftime('%Y-%m-%d %H:%M')}")

    # Recording controls
    if not st.session_state.recording:
        if st.button("🎤 Start Recording", type="primary", use_container_width=True):
            meeting_id = start_meeting(meeting_title)
            if meeting_id:
                st.session_state.recording = True
                st.session_state.current_meeting_id = meeting_id
                st.session_state.transcript = []
                st.session_state.summary = None
                st.success(f"🎤 Started recording meeting: {meeting_title}")
                st.info("💡 Speak clearly into your microphone. The system will transcribe your speech in real-time.")
                st.rerun()
    else:
        col_start, col_stop = st.columns(2)
        with col_start:
            st.button("⏸️ Pause", disabled=True, use_container_width=True)
        with col_stop:
            if st.button("⏹️ Stop Recording", type="secondary", use_container_width=True):
                if st.session_state.current_meeting_id:
                    success = stop_meeting(st.session_state.current_meeting_id)
                    if success:
                        st.session_state.recording = False
                        # Get final results
                        transcript, summary = get_meeting_data(st.session_state.current_meeting_id)
                        st.session_state.transcript = transcript
                        st.session_state.summary = summary
                        st.success("🛑 Meeting recording stopped!")
                        if transcript:
                            st.info(f"📝 Transcribed {len(transcript)} speech segments")
                        if summary:
                            st.info("🤖 AI summary generated successfully!")
                        st.rerun()
                    else:
                        st.error("❌ Failed to stop recording")

    # Recording status
    if st.session_state.recording:
        st.info("🔴 Recording in progress... Speak clearly into your microphone!")
        status_placeholder = st.empty()

        # Show current transcript length
        if st.session_state.transcript:
            st.metric("📝 Live Transcript", f"{len(st.session_state.transcript)} segments")

        # Auto-refresh transcript during recording
        if st.button("🔄 Refresh Transcript"):
            if st.session_state.current_meeting_id:
                transcript, _ = get_meeting_data(st.session_state.current_meeting_id)
                st.session_state.transcript = transcript
                st.success(f"Refreshed! {len(transcript)} segments transcribed so far.")
    else:
        st.info("⚪ Ready to record - Click 'Start Recording' to begin")

with col2:
    st.header("Meeting Intelligence")

    if st.session_state.transcript:
        # Create tabs
        tab1, tab2, tab3, tab4 = st.tabs(["📄 Transcript", "📋 Summary", "💬 Chat", "📊 Analytics"])

        # --- Tab 1: Transcript ---
        with tab1:
            st.subheader("Live Transcript")
            transcript_container = st.container()
            with transcript_container:
                for entry in st.session_state.transcript:
                    speaker = entry.get("speaker", "Unknown")
                    text = entry.get("text", "")
                    
                    # Color code speakers
                    if "Speaker 1" in speaker:
                        st.markdown(f"**🟢 {speaker}:** {text}")
                    elif "Speaker 2" in speaker:
                        st.markdown(f"**🔵 {speaker}:** {text}")
                    else:
                        st.markdown(f"**⚪ {speaker}:** {text}")

        # --- Tab 2: Summary ---
        with tab2:
            st.subheader("Meeting Summary")
            if st.session_state.summary:
                st.markdown("""
                <style>
                .summary-box {
                    background-color: #f0f2f6;
                    color: #000000;
                    border-radius: 10px;
                    padding: 20px;
                    border-left: 5px solid #ff4b4b;
                }
                </style>
                """, unsafe_allow_html=True)
                
                st.markdown(f'<div class="summary-box">{st.session_state.summary}</div>', unsafe_allow_html=True)
                
                # Download button
                if st.session_state.current_meeting_id:
                    content, filename = export_meeting(st.session_state.current_meeting_id)
                    if content:
                        st.download_button(
                            label="📥 Download Full Meeting Notes",
                            data=content,
                            file_name=filename,
                            mime="text/plain"
                        )
            else:
                st.info("Summary will appear here after the meeting ends.")

        # --- Tab 3: Chat (RAG) ---
        with tab3:
            st.subheader("Chat with your Meeting")
            
            # Chat history in session state
            if "chat_history" not in st.session_state:
                st.session_state.chat_history = []
            
            # Display chat history
            for msg in st.session_state.chat_history:
                with st.chat_message(msg["role"]):
                    st.write(msg["content"])
            
            # Chat input
            if prompt := st.chat_input("Ask a question about this meeting..."):
                # Add user message
                st.session_state.chat_history.append({"role": "user", "content": prompt})
                with st.chat_message("user"):
                    st.write(prompt)
                
                # Get AI response
                with st.chat_message("assistant"):
                    with st.spinner("Thinking..."):
                        answer = chat_with_meeting(st.session_state.current_meeting_id, prompt)
                        st.write(answer)
                
                # Add assistant message
                st.session_state.chat_history.append({"role": "assistant", "content": answer})

        # --- Tab 4: Analytics ---
        with tab4:
            st.subheader("Meeting Analytics")
            
            if st.button("📊 Generate Analytics"):
                with st.spinner("Analyzing meeting data..."):
                    analytics = get_analytics(st.session_state.current_meeting_id)
                    
                    if analytics:
                        # 1. Talk Time
                        st.markdown("### 🗣️ Talk Time Distribution")
                        talk_time = analytics.get("talk_time", {})
                        if talk_time:
                            st.bar_chart(talk_time)
                        else:
                            st.info("Not enough data for talk time analysis.")
                        
                        # 2. Sentiment
                        st.markdown("### 😊 Sentiment Analysis")
                        sentiment = analytics.get("sentiment", {})
                        
                        col_s1, col_s2 = st.columns(2)
                        with col_s1:
                            st.metric("Overall Tone", sentiment.get("overall", "Unknown"))
                        with col_s2:
                            score = sentiment.get("score", 0)
                            st.metric("Sentiment Score", f"{score:.2f}")
                            st.progress((score + 1) / 2) # Normalize -1..1 to 0..1
                            
                        if "explanation" in sentiment:
                            st.info(f"💡 {sentiment['explanation']}")
                    else:
                        st.error("Failed to generate analytics.")
    else:
        st.info("Start a recording or load a meeting to see details.")

# Previous meetings section
st.header("📚 Previous Meetings")

meetings = list_meetings()

if meetings:
    for meeting in meetings:
        with st.expander(f"📅 {meeting['title']} - {meeting['created_at'][:19]}"):
            col1, col2, col3, col4 = st.columns([1.5, 1, 1, 1])

            with col1:
                if st.button(f"📂 Load", key=f"load_{meeting['id']}"):
                    transcript, summary = get_meeting_data(meeting['id'])
                    st.session_state.transcript = transcript
                    st.session_state.summary = summary
                    st.success(f"Loaded meeting: {meeting['title']}")
                    st.rerun()

            with col2:
                st.metric("📝 Segments", meeting['transcript_count'])

            with col3:
                if meeting['has_summary']:
                    st.success("🤖 AI Summary")
                else:
                    st.warning("No Summary")

            with col4:
                col_del, col_exp = st.columns(2)

                with col_del:
                    if st.button(f"🗑️", key=f"delete_{meeting['id']}", help="Delete meeting"):
                        if st.session_state.get('confirm_delete') == meeting['id']:
                            # Actually delete
                            success = delete_meeting(meeting['id'])
                            if success:
                                st.success(f"✅ Deleted: {meeting['title']}")
                                # Clear confirmation state and force refresh
                                if 'confirm_delete' in st.session_state:
                                    del st.session_state.confirm_delete
                                time.sleep(0.5)  # Brief pause for user to see success message
                                st.rerun()
                            else:
                                st.error("❌ Failed to delete meeting")
                                st.session_state.confirm_delete = None
                        else:
                            # Show confirmation
                            st.session_state.confirm_delete = meeting['id']
                            st.warning(f"⚠️ Click 🗑️ again to confirm deletion of '{meeting['title']}'")
                            # Don't rerun here to show the warning

                with col_exp:
                    # Only show download button if meeting has content (transcript or summary)
                    if meeting['transcript_count'] > 0 or meeting['has_summary']:
                        content, filename = export_meeting(meeting['id'])
                        if content:
                            st.download_button(
                                label="📥",
                                data=content,
                                file_name=filename,
                                mime="text/plain",
                                help="Download meeting notes",
                                key=f"download_{meeting['id']}"
                            )
                        else:
                            st.button("📥", disabled=True, help="No content to download", key=f"download_disabled_{meeting['id']}")
                    else:
                        st.button("📥", disabled=True, help="No transcript or summary available", key=f"download_empty_{meeting['id']}")

            # Show preview if transcript exists
            if st.session_state.transcript and st.session_state.current_meeting_id == meeting['id']:
                st.markdown("**Preview:**")
                if st.session_state.transcript:
                    preview_text = st.session_state.transcript[0].get("text", "")[:100] + "..."
                    st.text(preview_text)
else:
    st.info("No previous meetings found.")

# Footer
st.markdown("---")
st.markdown("*Powered by AI - Inspired by the Quick Quotes Quill from Harry Potter*")

# Auto-refresh during recording
if st.session_state.recording:
    time.sleep(3)  # Refresh every 3 seconds to show live transcription
    st.rerun()