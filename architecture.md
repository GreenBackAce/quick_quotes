# Meeting Notes Taker and Summarizer - Architecture Overview

## Project Overview
An AI-powered application inspired by the Quick Quotes Quill from Harry Potter, designed to actively listen to meetings, distinguish speakers, transcribe conversations, and generate summaries using LLM technology.

## Core Requirements
- **Real-time Audio Processing**: Capture audio from meetings in real-time
- **Speaker Diarization**: Identify and distinguish different speakers
- **Transcription**: Convert speech to text with speaker attribution
- **Summarization**: Use Google Gemini LLM to generate meeting summaries
- **User Interface**: Simple web interface for controlling recording and viewing results
- **Data Storage**: Persist meeting notes and summaries

## Technology Stack
- **Language**: Python (for robustness and AI library ecosystem)
- **Backend**: FastAPI (RESTful API for processing)
- **Frontend**: Streamlit (simple web UI for user interaction)
- **Audio Processing**:
  - PyAudio: Audio capture
  - SpeechRecognition: Speech-to-text
  - pyannote.audio: Speaker diarization
- **LLM Integration**: Google Gemini API
- **Storage**: SQLite database
- **Platform**: Web browser (initial implementation)

## System Architecture

### High-Level Components
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Streamlit UI  │────│   FastAPI       │────│   Processing    │
│                 │    │   Backend       │    │   Pipeline      │
│ - Start/Stop    │    │                 │    │                 │
│ - Display       │    │ - API Endpoints │    │ - Audio Capture │
│   Results       │    │ - WebSocket     │    │ - Transcription │
└─────────────────┘    │   (optional)    │    │ - Diarization   │
                       └─────────────────┘    │ - Summarization │
                                              └─────────────────┘
```

### Data Flow
1. User starts recording via Streamlit UI
2. Browser captures audio and streams to FastAPI backend
3. Backend processes audio in chunks:
   - Speech recognition for transcription
   - Speaker diarization for voice identification
   - Accumulates transcript with speaker labels
4. At meeting end or on demand, sends transcript to Google Gemini for summarization
5. Stores results in database and displays in UI

### Key Technical Considerations
- **Real-time Processing**: Balance between real-time updates and processing accuracy
- **Audio Quality**: Handle various microphone setups and background noise
- **Privacy**: Audio data processing should be local where possible
- **Scalability**: Design for multiple concurrent meetings
- **Error Handling**: Graceful degradation when services are unavailable

## Implementation Phases
1. Project setup and basic structure
2. Audio capture and transcription
3. Speaker diarization integration
4. LLM summarization
5. UI development
6. Data persistence
7. Testing and optimization

## Dependencies
- fastapi
- streamlit
- pyaudio
- speechrecognition
- pyannote.audio
- google-generativeai
- sqlite3
- uvicorn (for FastAPI server)

## Security Considerations
- API key management for Google Gemini
- Audio data handling and privacy
- Input validation and sanitization

## Future Extensions
- Mobile app versions
- Desktop application
- Integration with calendar/meeting platforms
- Advanced analytics and insights
- Multi-language support