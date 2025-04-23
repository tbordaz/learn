#!/bin/bash

# Run Log Analysis System UI

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python -m venv venv
    source venv/bin/activate
    echo "Installing dependencies..."
    pip install -r requirements.txt
else
    source venv/bin/activate
fi

# Start Streamlit UI
echo "Starting Streamlit UI..."
streamlit run ui_app.py

echo "UI stopped." 