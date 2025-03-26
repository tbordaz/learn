import os
import json
import urllib.parse
import urllib.request
import base64
import boto3
import time

def handler(event, context):
    """
    Lambda function that handles the OAuth callback from Cognito.
    Exchanges the authorization code for tokens and redirects to the app page.
    """
    # Get environment variables
    user_pool_domain = os.environ.get('USER_POOL_DOMAIN')
    client_id = os.environ.get('USER_POOL_CLIENT_ID')
    redirect_uri = os.environ.get('REDIRECT_URI')
    base_url = os.environ.get('BASE_URL', '')
    
    # Get the authorization code from the query parameters
    if 'queryStringParameters' not in event or not event['queryStringParameters']:
        return {
            'statusCode': 400,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({'error': 'No authorization code provided'})
        }
    
    code = event['queryStringParameters'].get('code')
    if not code:
        return {
            'statusCode': 400,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({'error': 'No authorization code provided'})
        }
    
    # Exchange the authorization code for tokens
    try:
        token_endpoint = f"{user_pool_domain}/oauth2/token"
        
        data = {
            'grant_type': 'authorization_code',
            'client_id': client_id,
            'code': code,
            'redirect_uri': redirect_uri
        }
        
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        
        data = urllib.parse.urlencode(data).encode('utf-8')
        req = urllib.request.Request(token_endpoint, data=data, headers=headers, method='POST')
        
        with urllib.request.urlopen(req) as response:
            token_response = json.loads(response.read().decode('utf-8'))
            
        id_token = token_response.get('id_token')
        access_token = token_response.get('access_token')
        refresh_token = token_response.get('refresh_token')
        
        if not id_token or not access_token:
            return {
                'statusCode': 500,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({'error': 'Failed to retrieve tokens'})
            }
        
        # Create a simple HTML page that stores tokens in localStorage and redirects
        html_response = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Authentication Complete</title>
            <script>
                // Store tokens in localStorage
                localStorage.setItem('id_token', '{id_token}');
                localStorage.setItem('access_token', '{access_token}');
                localStorage.setItem('refresh_token', '{refresh_token}');
                localStorage.setItem('token_expiry', '{int(time.time()) + 3600}');
                
                // Redirect to the app page
                window.location.href = '{base_url}/app';
            </script>
        </head>
        <body>
            <h1>Authentication Successful</h1>
            <p>Redirecting to the application...</p>
        </body>
        </html>
        """
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'text/html',
                'Access-Control-Allow-Origin': '*'
            },
            'body': html_response
        }
        
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({'error': f'Error exchanging code for tokens: {str(e)}'})
        } 