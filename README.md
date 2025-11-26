# Quick Quotes Quill - AI Meeting Notes Taker

An intelligent meeting transcription and analysis system powered by AI, featuring real-time speaker diarization, automatic summarization, and remote GPU processing.

## Features

- **🎙️ Real-time Audio Transcription**: High-quality speech-to-text using faster-whisper
- **👥 Speaker Diarization**: Automatic speaker identification and separation using PyAnnote
- **📝 Intelligent Summarization**: AI-powered meeting summaries using Google Gemini
- **💬 Meeting Chat**: Ask questions about your meetings using RAG
- **📊 Analytics**: Talk time analysis and sentiment tracking
- **☁️ Remote GPU Processing**: Optional cloud-based GPU processing via Modal
- **🎨 Modern UI**: Clean, responsive Streamlit interface

## Architecture

### Backend (`backend/`)
- **FastAPI Server**: REST API for meeting management
- **Audio Processing Pipeline**:
  - Enhanced transcription with noise reduction
  - Speaker diarization with word-level alignment
  - Smart silence detection and audio preprocessing
- **Database**: SQLite for meeting storage
- **Remote GPU**: Optional Modal-based cloud processing

### Frontend (`frontend/`)
- **Streamlit App**: Interactive UI for recording, viewing, and analyzing meetings
- **Real-time Updates**: Live transcription display
- **Multi-tab Interface**: Transcript, Summary, Chat, and Analytics views

## Setup

### Prerequisites
```bash
# Python 3.8+
# ffmpeg (for audio processing)
sudo apt-get install ffmpeg  # Ubuntu/Debian
brew install ffmpeg          # macOS
```

### Installation

1. **Clone and navigate to project**:
```bash
cd /path/to/quick_quotes
```

2. **Create virtual environment**:
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate     # Windows
```

3. **Install dependencies**:
```bash
pip install -r requirements.txt
```

4. **Configure environment**:
Create a `.env` file with:
```bash
GOOGLE_API_KEY=your_gemini_api_key
HUGGINGFACE_TOKEN=your_hf_token  # For PyAnnote diarization
```

5. **Configure settings** (optional):
Edit `config.py` to customize:
- Audio settings (sample rate, chunk size)
- Model configurations
- Remote GPU settings (`USE_REMOTE_GPU = True/False`)

### Running the Application

```bash
python run.py
```

This starts both:
- **Frontend**: http://localhost:8501
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs

## Usage

### Upload Audio File
1. Navigate to the Upload tab
2. Select an audio file (WAV, MP3, M4A, etc.)
3. Enter a meeting title (optional)
4. Click upload and wait for processing

### View Results
- **Transcript Tab**: See speaker-separated transcript
- **Summary Tab**: View AI-generated meeting summary
- **Chat Tab**: Ask questions about the meeting
- **Analytics Tab**: View talk time and engagement metrics

## Remote GPU Processing

For faster processing of large files, enable remote GPU processing via Modal:

1. **Install Modal CLI**:
```bash
pip install modal
modal token new
```

2. **Deploy Worker**:
```bash
modal deploy backend/modal_worker.py
```

3. **Enable in Config**:
```python
# config.py
USE_REMOTE_GPU = True
```

The system will automatically use cloud GPUs for processing and fall back to local CPU if unavailable.

## Project Structure

```
quick_quotes/
├── backend/
│   ├── main.py                 # FastAPI application
│   ├── audio_processor.py      # Audio preprocessing
│   ├── enhanced_transcriber.py # Whisper transcription
│   ├── diarizer.py            # Speaker diarization
│   ├── summarizer.py          # AI summarization
│   ├── modal_worker.py        # Remote GPU worker
│   ├── modal_client.py        # Modal client helper
│   └── database.py            # SQLite management
├── frontend/
│   └── app.py                 # Streamlit UI
├── audio_test_files/          # Test audio samples
├── _archive/                  # Archived debug scripts
├── config.py                  # Configuration
├── run.py                     # Application launcher
└── requirements.txt           # Dependencies
```

## Configuration

### Audio Settings
- `SAMPLE_RATE`: 16000 Hz (optimal for Whisper)
- `CHUNK_DURATION_MS`: 30000 ms (30 seconds)
- `MAX_FILE_SIZE_MB`: 500 MB

### Model Settings
- **Whisper Model**: `base` (configurable: tiny, base, small, medium, large)
- **Diarization**: PyAnnote speaker-diarization-3.1
- **Summarization**: Google Gemini 1.5 Flash

### Remote GPU
- **Platform**: Modal
- **GPU**: Any available CUDA GPU
- **Timeout**: 30 minutes
- **Auto-scaling**: Enabled

## Development

### Debug Mode
Archived debug scripts are in `_archive/debug_scripts/`:
- `debug_diarization.py` - Test speaker diarization
- `monitor_test.py` - Monitor transcription pipeline
- `verify_*.py` - Various verification scripts

### Database Inspection
```bash
python _archive/debug_scripts/inspect_db.py
```

## Performance

- **Local CPU**: ~0.2x real-time (slow for long meetings)
- **Remote GPU (Modal)**: ~5.3x real-time (T4 GPU)
- **Diarization Accuracy**: >90% for clear audio with distinct speakers
- **Transcription WER**: <10% for clear English audio

## Troubleshooting

### Common Issues

1. **Port Already in Use**:
```bash
# Kill existing processes
pkill -f streamlit
pkill -f uvicorn
```

2. **Missing CUDA for Local GPU**:
- Install CUDA toolkit for your system
- Or enable `USE_REMOTE_GPU = True`

3. **HuggingFace Token Error**:
- Ensure `.env` has valid `HUGGINGFACE_TOKEN`
- Accept PyAnnote model terms at https://huggingface.co/pyannote/speaker-diarization-3.1

4. **API Rate Limits**:
- Gemini: 15 requests/minute (free tier)
- Reduce `summarizer.py` chunk size if hitting limits

## Future Enhancements

- [ ] Multi-language support
- [ ] Real-time streaming transcription
- [ ] Export to multiple formats (PDF, DOCX)
- [ ] Calendar integration
- [ ] Custom vocabulary/terminology
- [ ] Speaker labeling (assign names)

## License

MIT License - See LICENSE file for details

## Acknowledgments

- **faster-whisper**: Fast Whisper implementation
- **PyAnnote**: Speaker diarization models
- **Google Gemini**: Summarization and chat
- **Modal**: Serverless GPU infrastructure
- **Streamlit**: Frontend framework