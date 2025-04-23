# Log Analysis System

A simple log analysis tool.

## Overview

This system helps with intelligent log analysis by:
- Finding and extracting relevant logs
- Analyzing patterns and anomalies
- Recommending solutions based on identified issues

## Architecture

The system uses the following components:

### Core Components
- **Log Finder**: Searches and finds log files matching specific criteria
- **Log Parser**: Extracts structured data from log files
- **Pattern Analyzer**: Identifies trends and patterns in logs
- **Solution Recommender**: Suggests fixes based on identified issues

## Installation

### Requirements
- Python 3.9+

For Mac:
```bash
brew install python
```

### Setup

1. Clone the repository and run the setup script:
```bash
git clone https://github.com/yourusername/log-analysis-system.git
cd log-analysis-system
chmod +x setup.sh
./setup.sh
```

2. The setup script will:
   - Create a virtual environment
   - Install dependencies
   - Set up the directory structure
   - Generate sample log files

## Usage

### Log Analysis

For a comprehensive log analysis:
```bash
./run_simple_analysis.sh --logs data/logs --term error
```

#### Options
- `--logs PATH`: Directory containing log files
- `--term STRING`: Search term to look for in logs
- `--output FILE`: Write results to a JSON file
- `--verbose`: Enable detailed output

### Web Interface

To launch the Streamlit web UI:
```bash
./run_ui.sh
```

### Demo Mode

To run a demonstration with automatically generated logs:
```bash
./run_demo.sh
```

## Extending the System

### Adding New Log Sources

1. Update the log parsing functions in `analyze_logs.py` to support new log formats
2. Add new regex patterns to extract data from different log formats

### Adding New Solution Patterns

1. Enhance the `suggest_solutions` function in `analyze_logs.py`
2. Add new pattern matching logic for different types of issues
