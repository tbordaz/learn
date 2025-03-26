import json
import os
import boto3
from botocore.exceptions import ClientError

def handler(event, context):
    # Print the event for debugging
    print(json.dumps(event))
    
    # Get the claims from the event
    claims = event.get('requestContext', {}).get('authorizer', {}).get('claims', {})
    
    # Check for groups attributes in multiple formats
    custom_groups = claims.get('custom:groups', '')
    cognito_groups = claims.get('cognito:groups', '')
    
    print(f"custom:groups: {custom_groups}")
    print(f"cognito:groups: {cognito_groups}")
    
    # The admin group ID to check for
    admin_group_id = 'marketplace-admins'
    
    # Check if the user is in the admin group
    is_admin = False
    
    # Check in cognito:groups (from Cognito local groups)
    if cognito_groups and admin_group_id in cognito_groups:
        is_admin = True
        print(f"Found admin group via cognito:groups: {cognito_groups}")
    
    # Check in custom:groups (for Entra ID integration)
    elif custom_groups and admin_group_id in custom_groups:
        is_admin = True
        print(f"Found admin group via custom:groups direct match: {custom_groups}")
    
    # Check in custom:groups in list format
    elif custom_groups and custom_groups.startswith('[') and custom_groups.endswith(']'):
        groups_content = custom_groups[1:-1].strip()
        group_ids = [g.strip() for g in groups_content.split(',')]
        
        print(f"Parsed group IDs: {group_ids}")
        
        if admin_group_id in group_ids:
            is_admin = True
    
    # User is not an admin
    if not is_admin:
        print(f"User is not an admin. Did not find group ID {admin_group_id} in groups")
        return {
            'statusCode': 403,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps('Access denied: You do not have admin permissions')
        }
    
    # User is confirmed as admin, proceed with the request
    print(f"User has admin access. Found group ID {admin_group_id} in groups")
    
    # Return a simple admin dashboard response
    return {
        'statusCode': 200,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*'
        },
        'body': json.dumps({
            'message': 'Admin access granted successfully',
            'adminInfo': {
                'isAdmin': True,
                'adminGroupId': admin_group_id,
                'adminActions': ['View all users', 'Manage products', 'Configure settings']
            }
        })
    }