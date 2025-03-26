import json

def handler(event, context):
    """
    Public endpoint - returns a list of products.
    No authentication required.
    """
    products = [
        {"id": "1", "name": "Laptop", "price": 999.99, "description": "High-performance laptop"},
        {"id": "2", "name": "Smartphone", "price": 699.99, "description": "Latest smartphone model"},
        {"id": "3", "name": "Tablet", "price": 399.99, "description": "Lightweight tablet"},
        {"id": "4", "name": "Headphones", "price": 199.99, "description": "Noise-cancelling headphones"}
    ]
    
    return {
        'statusCode': 200,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Content-Type,Authorization',
            'Access-Control-Allow-Methods': 'GET,OPTIONS'
        },
        'body': json.dumps({"products": products})
    }