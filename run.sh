#!/bin/bash

# ASP Plagiarism Service Startup Script

echo "Starting ASP Plagiarism Service..."
echo ""

# Check if venv exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate venv
echo "Activating virtual environment..."
source venv/bin/activate

# Install/upgrade dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Start Flask app
echo ""
echo "============================================"
echo "Starting Flask server on port 5000..."
echo "============================================"
echo ""
echo "API will be available at:"
echo "http://localhost:5000"
echo ""
echo "Health check: http://localhost:5000/api/v1/detect/health"
echo ""

python app.py
