#!/bin/bash
echo "🚀 Starting ClawSquad MVP..."

# Install dependencies if needed
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
else
    source venv/bin/activate
fi

# Initialize database
echo "Initializing database..."
python3 server/models.py

# Start FastAPI server
echo "Starting FastAPI server on port 8000..."
uvicorn server.main:app --host 0.0.0.0 --port 8000 --reload