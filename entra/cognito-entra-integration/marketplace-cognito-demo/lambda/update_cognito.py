import json
import boto3
import os
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def handler(event, context):
    """
    This Lambda function updates the Cognito User Pool Client to
    toggle between local authentication and SAML federation.
    
    Parameters:
    - mode: 'local' for Cognito-only authentication, 'saml' for SAML federation
    - samlProviderName: Name of the SAML provider (default 'EntraID')
    """
    try:
        user_pool_id = os.environ['USER_POOL_ID']
        client_id = os.environ['USER_POOL_CLIENT_ID']
        
        # Parse request body
        body = {}
        if isinstance(event.get('body'), str):
            try:
                body = json.loads(event.get('body', '{}'))
            except:
                pass
        elif isinstance(event.get('body'), dict):
            body = event.get('body', {})
        
        # Get parameters
        mode = body.get('mode', 'local')  # Default to local auth
        saml_provider_name = body.get('samlProviderName', 'EntraID')
        
        client = boto3.client('cognito-idp')
        
        # Get current client configuration
        response = client.describe_user_pool_client(
            UserPoolId=user_pool_id,
            ClientId=client_id
        )
        
        client_config = response['UserPoolClient']
        
        # Configure based on mode
        if mode == 'saml':
            # Update to use SAML provider
            updated_providers = ['COGNITO', saml_provider_name]
            
            # Update the client configuration to use SAML
            response = client.update_user_pool_client(
                UserPoolId=user_pool_id,
                ClientId=client_id,
                SupportedIdentityProviders=updated_providers,
                AllowedOAuthFlows=client_config.get('AllowedOAuthFlows', []),
                AllowedOAuthFlowsUserPoolClient=client_config.get('AllowedOAuthFlowsUserPoolClient', True),
                AllowedOAuthScopes=client_config.get('AllowedOAuthScopes', []),
                CallbackURLs=client_config.get('CallbackURLs', []),
                LogoutURLs=client_config.get('LogoutURLs', []),
                # Make SAML the preferred provider
                IdentityProviderName=saml_provider_name
            )
            
            message = "Successfully configured for SAML federation with Entra ID"
            details = "Local users can no longer authenticate directly. Only federated users through SAML can login."
        else:
            # Update for local Cognito authentication only
            updated_providers = ['COGNITO']
            
            # Update the client configuration for local authentication
            response = client.update_user_pool_client(
                UserPoolId=user_pool_id,
                ClientId=client_id,
                SupportedIdentityProviders=updated_providers,
                AllowedOAuthFlows=client_config.get('AllowedOAuthFlows', []),
                AllowedOAuthFlowsUserPoolClient=client_config.get('AllowedOAuthFlowsUserPoolClient', True),
                AllowedOAuthScopes=client_config.get('AllowedOAuthScopes', []),
                CallbackURLs=client_config.get('CallbackURLs', []),
                LogoutURLs=client_config.get('LogoutURLs', [])
                # No IdentityProviderName to allow local authentication
            )
            
            message = "Successfully configured for local Cognito authentication"
            details = "Local users can now authenticate with Cognito. SAML federation is disabled."
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'message': message,
                'details': details,
                'mode': mode
            })
        }
    except Exception as e:
        logger.error(f"Error updating Cognito configuration: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'message': 'Error updating Cognito configuration',
                'error': str(e)
            })
        }