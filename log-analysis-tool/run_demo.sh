#!/bin/bash

# Run Log Analysis System in Demo Mode

# Default Ollama model
OLLAMA_MODEL=${OLLAMA_MODEL:-"llama3.2"}
DISABLE_AI=""

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --model)
            OLLAMA_MODEL="$2"
            shift; shift
            ;;
        --disable-ai)
            DISABLE_AI="--disable-ai"
            shift
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

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

# Check if Ollama AI is being used
if [ -z "$DISABLE_AI" ]; then
    echo "Using Ollama model: $OLLAMA_MODEL"
    export OLLAMA_MODEL="$OLLAMA_MODEL"
    
    # Check if Ollama is running
    if ! curl -s http://localhost:11434/api/version >/dev/null 2>&1; then
        echo "⚠️ Warning: Ollama server is not running. Start it with 'ollama serve'"
        echo "Continuing with AI enhancement disabled"
        DISABLE_AI="--disable-ai"
    fi
else
    echo "AI enhancement is disabled"
fi

# Generate fresh demo logs
echo "Generating demo log files..."
python3 -c "
import os
import random
from datetime import datetime, timedelta

# Create data directory if it doesn't exist
os.makedirs('data/logs', exist_ok=True)

def generate_log_file(filename, log_type, entries=200):
    with open(filename, 'w') as f:
        timestamp = datetime.now() - timedelta(hours=random.randint(1, 24))
        
        for _ in range(entries):
            timestamp += timedelta(seconds=random.randint(1, 60))
            time_str = timestamp.strftime('%Y-%m-%d %H:%M:%S')
            
            if log_type == 'connection':
                if random.random() < 0.8:  # 80% are errors
                    component = random.choice(['NetworkService', 'DatabaseClient', 'AppServer'])
                    message = random.choice([
                        'Connection timeout to remote service',
                        'Failed to establish connection with server',
                        'Network connection interrupted',
                        'Database operation failed: could not connect to server',
                        'Failed to execute query: connection reset'
                    ])
                    severity = 'ERROR'
                else:
                    component = random.choice(['NetworkService', 'DatabaseClient', 'AppServer'])
                    message = random.choice([
                        'Connection established successfully',
                        'Query executed successfully',
                        'Network status: online'
                    ])
                    severity = random.choice(['INFO', 'DEBUG'])
            
            log_line = f'{time_str} {severity} [{component}]: {message}'
            f.write(log_line + '\\n')

# Generate files with current timestamp
timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
generate_log_file(f'data/logs/connection_issue_demo_{timestamp}.log', 'connection')
print(f'Generated log file: data/logs/connection_issue_demo_{timestamp}.log')
"

# Run analysis
echo "Running analysis on generated logs..."
./analyze_logs.py --logs ./data/logs --term error --verbose $DISABLE_AI

echo "Demo complete."
echo
if [ -z "$DISABLE_AI" ]; then
    echo "✅ Analysis completed with Ollama model: $OLLAMA_MODEL"
else 
    echo "⚠️ Analysis completed with AI enhancement disabled"
fi 