# Log Analysis System - Docker Version

This directory contains a Dockerized version of the Log Analysis System.

## Overview

The containerized version allows you to:
- Run the log analysis tool in an isolated environment
- Access log files from the host system
- Analyze external system logs without installing dependencies on the host

## Directory Structure

```
docker/
├── .env                    # Environment variable configuration
├── Dockerfile              # Container definition
├── docker-compose.yml      # Service orchestration
└── app/                    # Application code
    ├── analyze_logs.py     # Log analysis script
    ├── ui_app.py           # Streamlit web UI
    ├── requirements.txt    # Python dependencies
    └── data/logs/          # Sample log files
```

## Running the Container

### Prerequisites
- Docker
- Docker Compose

### Quick Start

1. Configure the external logs directory in `.env` (optional, defaults to `/var/log`):
   ```
   EXTERNAL_LOGS_DIR=/path/to/your/logs
   ```

2. Build and start the container:
   ```bash
   cd docker
   docker-compose up --build
   ```

3. Access the web UI at http://localhost:8501

## How External Logs Are Accessed

The container mounts the host's log directory (configurable via the `EXTERNAL_LOGS_DIR` environment variable) into the container at `/external_logs`.

This volume mounting approach allows the containerized application to read log files directly from the host system without copying them into the container.

Key advantages:
- Real-time access to updated log files
- No need to copy large log files into the container
- Access to logs from any system directory without container modifications

## Customization

### Using Different Log Sources

1. Update the `.env` file with your log directory path:
   ```
   EXTERNAL_LOGS_DIR=/custom/path/to/logs
   ```

2. Restart the container:
   ```bash
   docker-compose down
   docker-compose up
   ```

### Persistent Sample Logs

If you want to use your own sample logs:
1. Place your log files in the `app/data/logs/` directory
2. Rebuild and restart the container:
   ```bash
   docker-compose up --build
   ``` 