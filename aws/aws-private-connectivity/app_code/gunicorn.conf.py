import os

# Bind to 0.0.0.0 to listen on all interfaces
bind = "0.0.0.0:" + os.environ.get("PORT", "8080")

# Worker configuration
workers = 2
threads = 4
worker_class = "sync"

# Request handling
max_requests = 1000
max_requests_jitter = 50
timeout = 30

# Logging
accesslog = "-"  # Log to stdout
errorlog = "-"   # Log to stderr
loglevel = "info"

# Startup and shutdown
graceful_timeout = 10
keepalive = 2 