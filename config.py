"""
Configuration settings for Quick Quotes Quill
"""

import os
from typing import Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    """Application configuration"""

    # API Keys
    GOOGLE_API_KEY: Optional[str] = os.getenv("GOOGLE_API_KEY")
    HUGGINGFACE_TOKEN: Optional[str] = os.getenv("HUGGINGFACE_TOKEN")

    # Audio settings
    SAMPLE_RATE: int = 16000
    CHANNELS: int = 1
    CHUNK_SIZE: int = 1024
    AUDIO_FORMAT = "paInt16"

    # Processing settings
    TRANSCRIPTION_CHUNK_DURATION: int = 3  # seconds
    DIARIZATION_ENABLED: bool = bool(HUGGINGFACE_TOKEN)

    # Database settings
    DATABASE_PATH: str = "meetings.db"

    # API settings
    BACKEND_HOST: str = "0.0.0.0"
    BACKEND_PORT: int = 8000
    FRONTEND_PORT: int = 8501

    # LLM settings
    SUMMARY_MODEL: str = "gemini-2.0-flash"
    MAX_SUMMARY_LENGTH: int = 2000

    # Diarization settings
    DIARIZATION_MODEL: str = "pyannote/speaker-diarization-3.1"

    # Speech recognition settings
    DEFAULT_LANGUAGE: str = "en-US"
    WHISPER_MODEL_PREFERENCE: str = "large-v3"  # Options: tiny, base, small, medium, large-v3
    ENABLE_AUDIO_PREPROCESSING: bool = True
    AUDIO_CHUNK_MAX_DURATION: int = 30  # seconds
    AUDIO_SILENCE_THRESHOLD: int = -35  # dBFS
    
    # AI Noise Removal (Demucs)
    ENABLE_AI_NOISE_REMOVAL: bool = False  # Disabled by default as it's slow
    DEMUCS_MODEL: str = "htdemucs"  # Options: htdemucs (fast), htdemucs_ft (better)

    # Remote GPU Settings (Modal)
    USE_REMOTE_GPU: bool = True
    MODAL_APP_NAME: str = "quick-quotes-worker"
    MODAL_CLASS_NAME: str = "GPUWorker"

    @classmethod
    def validate(cls) -> list:
        """Validate configuration and return list of warnings/errors"""
        warnings = []

        if not cls.GOOGLE_API_KEY:
            warnings.append("GOOGLE_API_KEY not set - summarization will not work")

        if not cls.HUGGINGFACE_TOKEN:
            warnings.append("HUGGINGFACE_TOKEN not set - speaker diarization will use fallback method")

        return warnings

# Global config instance
config = Config()