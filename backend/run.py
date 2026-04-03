#!/usr/bin/env python
"""
Run script for Flask backend.
Usage: python run.py
"""
import sys
import os

# Add the backend directory to Python path
backend_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, backend_dir)

# Now import and run the app
from app.main import app

if __name__ == '__main__':
    print("Starting Smart Canteen Flask Server...")
    print("Server: http://localhost:8000")
    print("Health: http://localhost:8000/health")
    print("-" * 40)
    app.run(debug=True, host='0.0.0.0', port=8000)
