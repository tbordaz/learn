import json

def handler(event, context):
    """
    Public endpoint - returns details for a specific product.
    No authentication required.
    """
    products = {
        "1": {"id": "1", "name": "Laptop", "price": 999.99, "description": "High-performance laptop with 16GB RAM, 512GB SSD, and dedicated graphics card", "stock": 15, "sku": "LAP-2023-001"},
        "2": {"id": "2", "name": "Smartphone", "price": 699.99, "description": "Latest smartphone model with 6.7-inch OLED display, 128GB storage, and advanced camera system", "stock": 28, "sku": "PHN-2023-002"},
        "3": {"id": "3", "name": "Tablet", "price": 399.99, "description": "Lightweight tablet with 10-inch display, 64GB storage, and 10-hour battery life", "stock": 22, "sku": "TAB-2023-003"},
        "4": {"id": "4", "name": "Headphones", "price": 199.99, "description": "Over-ear noise-cancelling headphones with Bluetooth 5.2 and 30-hour battery life", "stock": 34, "sku": "AUD-2023-004"}
    }
    
    # Get product ID from path parameters
    product_id = event.get('pathParameters', {}).get('id')
    
    if not product_id or product_id not in products:
        return {
            'statusCode': 404,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type,Authorization',
                'Access-Control-Allow-Methods': 'GET,OPTIONS'
            },
            'body': json.dumps({"error": "Product not found"})
        }
    
    return {
        'statusCode': 200,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Content-Type,Authorization',
            'Access-Control-Allow-Methods': 'GET,OPTIONS'
        },
        'body': json.dumps(products[product_id])
    }