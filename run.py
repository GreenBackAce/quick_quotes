#!/usr/bin/env python3
"""
Quick Quotes Quill - Launcher script
"""

import subprocess
import sys
import os
import time
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def check_requirements():
    """Check if virtual environment and requirements are set up"""
    venv_path = Path("./venv")
    if not venv_path.exists():
        print("❌ Virtual environment not found. Please run setup first.")
        return False

    requirements_path = Path("./requirements.txt")
    if not requirements_path.exists():
        print("❌ requirements.txt not found.")
        return False

    return True

def start_backend():
    """Start the FastAPI backend"""
    print("🚀 Starting FastAPI backend...")
    backend_cmd = [
        "./venv/bin/python", "-m", "uvicorn",
        "backend.main:app",
        "--host", "0.0.0.0",
        "--port", "8000",
        "--reload"
    ]

    return subprocess.Popen(backend_cmd, cwd=os.getcwd())

def start_frontend():
    """Start the Streamlit frontend"""
    print("🎨 Starting Streamlit frontend...")
    # Give backend a moment to start
    time.sleep(2)

    frontend_cmd = [
        "./venv/bin/streamlit", "run", "frontend/app.py",
        "--server.port", "8501",
        "--server.address", "0.0.0.0"
    ]

    return subprocess.Popen(frontend_cmd, cwd=os.getcwd())

def main():
    """Main launcher function"""
    print("📝 Quick Quotes Quill - AI Meeting Notes Taker")
    print("=" * 50)

    if not check_requirements():
        print("\nTo set up the project:")
        print("1. python3 -m venv venv")
        print("2. ./venv/bin/pip install -r requirements.txt")
        print("3. Set environment variables: GOOGLE_API_KEY and optionally HUGGINGFACE_TOKEN")
        sys.exit(1)

    # Check environment variables
    if not os.getenv("GOOGLE_API_KEY") or os.getenv("GOOGLE_API_KEY") == "your-google-gemini-api-key-here":
        print("⚠️  Warning: GOOGLE_API_KEY not set in .env file")
        print("   Please add your Google Gemini API key to the .env file")
        print("   Summarization features will not work without it.")

    if not os.getenv("HUGGINGFACE_TOKEN") or os.getenv("HUGGINGFACE_TOKEN") == "your-huggingface-token-here":
        print("⚠️  Warning: HUGGINGFACE_TOKEN not set in .env file")
        print("   Speaker diarization will use fallback method.")
        print("   (Optional: Add HuggingFace token for better speaker diarization)")

    try:
        # Start backend
        backend_process = start_backend()

        # Start frontend
        frontend_process = start_frontend()

        print("\n✅ Services started!")
        print("📱 Frontend: http://localhost:8501")
        print("🔧 Backend API: http://localhost:8000")
        print("📚 API Docs: http://localhost:8000/docs")
        print("\nPress Ctrl+C to stop all services...")

        # Wait for processes
        try:
            backend_process.wait()
            frontend_process.wait()
        except KeyboardInterrupt:
            print("\n🛑 Shutting down services...")
            backend_process.terminate()
            frontend_process.terminate()
            backend_process.wait()
            frontend_process.wait()
            print("✅ All services stopped.")

    except Exception as e:
        print(f"❌ Error starting services: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()