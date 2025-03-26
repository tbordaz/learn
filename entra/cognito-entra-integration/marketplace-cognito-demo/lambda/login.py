import os
import json

def handler(event, context):
    """
    Lambda function that redirects to the Cognito hosted UI for authentication.
    """
    user_pool_domain = os.environ.get('USER_POOL_DOMAIN')
    client_id = os.environ.get('USER_POOL_CLIENT_ID')
    redirect_uri = os.environ.get('REDIRECT_URI')
    
    # Create the login URL for Cognito hosted UI
    login_url = f"{user_pool_domain}/login?client_id={client_id}&response_type=code&redirect_uri={redirect_uri}"
    
    # Return a redirect response
    return {
        'statusCode': 302,
        'headers': {
            'Location': login_url,
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Content-Type,Authorization',
            'Access-Control-Allow-Methods': 'GET,OPTIONS'
        },
        'body': json.dumps({'message': 'Redirecting to login page'})
    } 