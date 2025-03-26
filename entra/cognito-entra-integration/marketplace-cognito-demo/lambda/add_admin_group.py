import json
import boto3
import os
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def handler(event, context):
    """
    This Lambda function creates the marketplace-admins group if it doesn't exist
    and adds the specified user to the group.
    """
    try:
        user_pool_id = os.environ.get('USER_POOL_ID')
        
        # Default to testuser if no username is provided
        body = {}
        if isinstance(event.get('body'), str):
            try:
                body = json.loads(event.get('body', '{}'))
            except:
                pass
        elif isinstance(event.get('body'), dict):
            body = event.get('body', {})
            
        username = body.get('username', 'testuser')
        
        client = boto3.client('cognito-idp')
        
        # First check if the group exists
        try:
            client.get_group(
                GroupName='marketplace-admins',
                UserPoolId=user_pool_id
            )
            logger.info("marketplace-admins group already exists")
        except client.exceptions.ResourceNotFoundException:
            # Create the group
            logger.info("Creating marketplace-admins group")
            client.create_group(
                GroupName='marketplace-admins',
                UserPoolId=user_pool_id,
                Description='Administrators for the marketplace application'
            )
        
        # Add the user to the group
        client.admin_add_user_to_group(
            UserPoolId=user_pool_id,
            Username=username,
            GroupName='marketplace-admins'
        )
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'message': f'User {username} has been added to the marketplace-admins group',
                'username': username,
                'group': 'marketplace-admins'
            })
        }
    except Exception as e:
        logger.error(f"Error adding user to admin group: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'message': 'Error adding user to admin group',
                'error': str(e)
            })
        } 