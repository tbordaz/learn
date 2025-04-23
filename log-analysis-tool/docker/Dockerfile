FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Copy requirements file and install dependencies
COPY app/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code
COPY app/analyze_logs.py app/ui_app.py ./
COPY app/data/logs ./data/logs

# Make the script executable
RUN chmod +x analyze_logs.py

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Expose the port for Streamlit
EXPOSE 8501

# Run the Streamlit app
CMD ["streamlit", "run", "ui_app.py", "--server.address=0.0.0.0"]
