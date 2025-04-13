from flask import Flask, request
import requests
import os
import json

app = Flask(__name__)

@app.route('/')
def hello():
    # Try common headers for source IP, fallback to remote_addr
    source_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    return f"""
    <html>
    <head>
        <title>AWS Private Connectivity Demo</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 40px; }}
            h1 {{ color: #232f3e; }}
        </style>
    </head>
    <body>
        <h1>AWS Private Connectivity Demo</h1>
        <h2>Inbound Connection Information</h2>
        <p>Your request came from IP: <strong>{source_ip}</strong></p>
        <p><a href="/getmyip">Check My Outbound IP</a></p>
        <p>Deployment Mode: <strong>{os.environ.get('DEPLOYMENT_MODE', 'Unknown')}</strong></p>
    </body>
    </html>
    """

@app.route('/health')
def health():
    return "OK", 200

@app.route('/getmyip')
def get_my_ip():
    try:
        response = requests.get('https://ifconfig.me/ip', timeout=5)
        response.raise_for_status()
        my_outbound_ip = response.text.strip()
        
        return f"""
        <html>
        <head>
            <title>AWS Private Connectivity Demo - Outbound IP</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 40px; }}
                h1 {{ color: #232f3e; }}
            </style>
        </head>
        <body>
            <h1>AWS Private Connectivity Demo</h1>
            <h2>Outbound Connection Information</h2>
            <p>My outbound IP: <strong>{my_outbound_ip}</strong></p>
            <p>Deployment Mode: <strong>{os.environ.get('DEPLOYMENT_MODE', 'Unknown')}</strong></p>
            <p><a href="/">Back to Home</a></p>
        </body>
        </html>
        """
    except requests.exceptions.RequestException as e:
        return f"""
        <html>
        <head>
            <title>AWS Private Connectivity Demo - Error</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 40px; }}
                h1 {{ color: #232f3e; }}
            </style>
        </head>
        <body>
            <h1>AWS Private Connectivity Demo</h1>
            <h2>Outbound Connection Error</h2>
            <p>Error fetching outbound IP: <strong>{e}</strong></p>
            <p>This might be because outbound internet access is restricted.</p>
            <p>Deployment Mode: <strong>{os.environ.get('DEPLOYMENT_MODE', 'Unknown')}</strong></p>
            <p><a href="/">Back to Home</a></p>
        </body>
        </html>
        """

# Lambda handler function
def lambda_handler(event, context):
    """AWS Lambda function handler for API Gateway integration."""
    # Print event for debugging
    print('Event: ', event)
    
    # Extract HTTP method and path from the API Gateway event
    http_method = event.get('httpMethod', 'GET')
    path = event.get('path', '/')
    
    # Strip trailing slash if present
    if path != '/' and path.endswith('/'):
        path = path[:-1]
    
    # Handle empty or root path
    if not path or path == '/':
        path = '/'
    
    # Setup environment for Flask
    environ = {
        'REQUEST_METHOD': http_method,
        'PATH_INFO': path,
        'QUERY_STRING': event.get('queryStringParameters', {}),
        'REMOTE_ADDR': event.get('requestContext', {}).get('identity', {}).get('sourceIp', '127.0.0.1'),
        'HTTP_X_FORWARDED_FOR': event.get('headers', {}).get('X-Forwarded-For', ''),
        'wsgi.url_scheme': 'https'
    }
    
    # Add headers to environment
    for header, value in event.get('headers', {}).items():
        environ[f'HTTP_{header.replace("-", "_").upper()}'] = value
    
    # Create response holder
    response = {
        'statusCode': 200,
        'body': '',
        'headers': {
            'Content-Type': 'text/html'
        }
    }
    
    # Run the Flask app
    with app.request_context(environ):
        # Match the routes based on the path
        if path == '/':
            response['body'] = hello()
        elif path == '/health':
            response['body'] = health()[0]
            response['statusCode'] = health()[1]
        elif path == '/getmyip':
            response['body'] = get_my_ip()
        else:
            response['body'] = '<h1>404 Not Found</h1>'
            response['statusCode'] = 404
    
    return response

# Serve the app when run directly
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port) 