#!/bin/bash
set -e

echo "🚀 Starting Back End Health Agent..."

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python -m venv venv
fi

# Activate virtual environment
echo "✓ Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "📥 Installing dependencies..."
pip install -q --upgrade pip
pip install -q -r requirements.txt

# Start the server
echo "🌐 Starting uvicorn server..."
python -m uvicorn src.core.server:app --host 0.0.0.0 --port 8080 --reload
