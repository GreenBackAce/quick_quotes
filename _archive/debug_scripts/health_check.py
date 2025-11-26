#!/usr/bin/env python3
"""
Quick E2E Test for Quick Quotes Quill
Tests: Backend API, Database, Intelligence Features
"""

import requests
import sys

BACKEND_URL = "http://localhost:8000"

def test_backend_health():
    """Test if backend is responding"""
    try:
        response = requests.get(f"{BACKEND_URL}/meetings", timeout=5)
        if response.status_code == 200:
            print("✅ Backend API: Healthy")
            return True
        else:
            print(f"❌ Backend API: Unhealthy (status {response.status_code})")
            return False
    except Exception as e:
        print(f"❌ Backend API: Cannot connect - {e}")
        return False

def test_database():
    """Test database connectivity"""
    try:
        from backend.database import DatabaseManager
        db = DatabaseManager()
        db.init_db()
        meetings = db.list_meetings()
        print(f"✅ Database: Working ({len(meetings)} meetings found)")
        return True
    except Exception as e:
        print(f"❌ Database: Error - {e}")
        return False

def test_intelligence_module():
    """Test intelligence module imports"""
    try:
        from backend.intelligence import MeetingIntelligence
        mi = MeetingIntelligence()
        print(f"✅ Intelligence Module: Loaded")
        return True
    except Exception as e:
        print(f"❌ Intelligence Module: Error - {e}")
        return False

def test_frontend_files():
    """Test if frontend files exist"""
    import os
    frontend_path = "frontend/app.py"
    if os.path.exists(frontend_path):
        print(f"✅ Frontend: File exists")
        return True
    else:
        print(f"❌ Frontend: app.py not found")
        return False

if __name__ == "__main__":
    print("=" * 50)
    print("Quick Quotes Quill - Health Check")
    print("=" * 50)
    
    tests = [
        test_backend_health(),
        test_database(),
        test_intelligence_module(),
        test_frontend_files()
    ]
    
    print("=" * 50)
    if all(tests):
        print("🎉 All systems operational!")
        sys.exit(0)
    else:
        print("⚠️  Some systems are down")
        sys.exit(1)
