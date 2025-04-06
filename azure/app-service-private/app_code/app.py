from flask import Flask, request
import requests
import os

app = Flask(__name__)

@app.route('/')
def hello():
    # Try common headers for source IP, fallback to remote_addr
    source_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    return f"Hello! Your request came from IP: {source_ip}<br/><br/>" \
            f"Try /getmyip to see my outbound IP."

@app.route('/getmyip')
def get_my_ip():
    try:
        response = requests.get('https://ifconfig.me/ip', timeout=5)
        response.raise_for_status() # Raise an exception for bad status codes
        my_outbound_ip = response.text.strip()
        return f"When I make an outbound call, my source IP is: {my_outbound_ip}"
    except requests.exceptions.RequestException as e:
        return f"Error fetching outbound IP: {e}"

if __name__ == '__main__':
    # Port configuration for App Service
    port = int(os.environ.get('PORT', 8000))
    app.run(host='0.0.0.0', port=port)