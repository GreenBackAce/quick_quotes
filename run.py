#!/usr/bin/env python3
"""
Quick Quotes Quill - Launcher script
"""

import subprocess
import sys
import os
import time
import signal
import webbrowser
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

    # Start in new process group so we can kill all children
    return subprocess.Popen(
        backend_cmd, 
        cwd=os.getcwd(),
        preexec_fn=os.setsid if os.name != 'nt' else None
    )

def start_frontend():
    """Start the Next.js frontend"""
    print("🎨 Starting Next.js frontend...")
    # Give backend a moment to start
    time.sleep(2)

    frontend_cmd = ["npm", "run", "dev"]
    
    # Run in the frontend-next directory
    frontend_cwd = os.path.join(os.getcwd(), "frontend-next")

    # Start in new process group so we can kill all children
    return subprocess.Popen(
        frontend_cmd, 
        cwd=frontend_cwd,
        preexec_fn=os.setsid if os.name != 'nt' else None
    )

def kill_process_tree(process):
    """Kill a process and all its children"""
    if process.poll() is None:  # If process is still running
        try:
            if os.name != 'nt':
                # On Unix, kill the entire process group
                os.killpg(os.getpgid(process.pid), signal.SIGTERM)
            else:
                # On Windows, just terminate the process
                process.terminate()
            
            # Wait for termination with timeout
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                # Force kill if it doesn't terminate gracefully
                if os.name != 'nt':
                    os.killpg(os.getpgid(process.pid), signal.SIGKILL)
                else:
                    process.kill()
                process.wait()
        except ProcessLookupError:
            # Process already terminated
            pass

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

    backend_process = None
    frontend_process = None

    try:
        # Start backend
        backend_process = start_backend()

        # Start frontend
        frontend_process = start_frontend()

        print("\n✅ Services started!")
        print("📱 Frontend: http://localhost:3000")
        print("🔧 Backend API: http://localhost:8000")
        print("📚 API Docs: http://localhost:8000/docs")
        print("\nPress Ctrl+C to stop all services...")

        # Give services a moment to fully start, then open browser
        time.sleep(3)
        print("🌐 Opening browser...")
        webbrowser.open("http://localhost:3000")

        # Wait for processes
        try:
            backend_process.wait()
            frontend_process.wait()
        except KeyboardInterrupt:
            print("\n🛑 Shutting down services...")
            
            # Kill both process trees
            if frontend_process:
                kill_process_tree(frontend_process)
            if backend_process:
                kill_process_tree(backend_process)
            
            print("✅ All services stopped.")

    except Exception as e:
        print(f"❌ Error starting services: {e}")
        
        # Clean up any running processes
        if frontend_process:
            kill_process_tree(frontend_process)
        if backend_process:
            kill_process_tree(backend_process)
        
        sys.exit(1)

if __name__ == "__main__":
    main()