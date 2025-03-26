import json
import os

def handler(event, context):
    """
    Simple web app that displays user information and marketplace details
    with login/logout functionality.
    """
    user_pool_id = os.environ.get('USER_POOL_ID')
    client_id = os.environ.get('USER_POOL_CLIENT_ID')
    api_url = os.environ.get('API_URL', '')
    login_url = os.environ.get('LOGIN_URL', '')
    base_url = os.environ.get('BASE_URL', '')
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Marketplace Demo</title>
        <style>
            body {{
                font-family: Arial, sans-serif;
                line-height: 1.6;
                margin: 0;
                padding: 20px;
                max-width: 800px;
                margin: 0 auto;
            }}
            h1 {{
                color: #333;
                border-bottom: 1px solid #ddd;
                padding-bottom: 10px;
            }}
            .card {{
                border: 1px solid #ddd;
                border-radius: 5px;
                padding: 15px;
                margin-bottom: 20px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }}
            .button {{
                display: inline-block;
                background-color: #4CAF50;
                color: white;
                padding: 10px 15px;
                text-decoration: none;
                border-radius: 4px;
                margin-right: 10px;
            }}
            .button:hover {{
                background-color: #45a049;
            }}
            #login-section {{
                margin-bottom: 20px;
            }}
            #user-info {{
                display: none;
                margin-bottom: 20px;
            }}
            #product-list {{
                display: none;
            }}
            .product-card {{
                border: 1px solid #ddd;
                border-radius: 5px;
                padding: 15px;
                margin-bottom: 15px;
                background-color: #f9f9f9;
            }}
            .product-details {{
                margin-top: 10px;
                padding: 10px;
                background-color: #fff;
                border-radius: 4px;
                border: 1px solid #eee;
            }}
            .product-details h4 {{
                margin-top: 0;
                color: #4CAF50;
                border-bottom: 1px solid #eee;
                padding-bottom: 5px;
            }}
        </style>
    </head>
    <body>
        <h1>Marketplace Demo App</h1>
        <div class="card">
            <h2>Authentication Status</h2>
            <div id="login-status">
                <p>You are not logged in</p>
                <a href="{login_url}" class="button">Login</a>
            </div>
            <div id="user-info">
                <p>You are logged in as: <span id="username"></span></p>
                <button id="logout-button" class="button">Logout</button>
                <p><small>Token expires: <span id="token-expiry"></span></small></p>
            </div>
            <div style="margin-top: 15px;">
                <a href="{base_url}/app/config" style="color: #666; font-size: 0.9em;">Configuration Settings</a>
            </div>
        </div>
        
        <div class="card">
            <h2>Available Products</h2>
            <button id="load-products-button" class="button">Load Products</button>
            <div id="product-list"></div>
        </div>
        
        <div class="card">
            <h2>Protected Resources</h2>
            <button id="load-admin-button" class="button" disabled>Access Admin (Requires Admin Group)</button>
            <div id="admin-result"></div>
        </div>
        
        <script>
            // Base URLs for API requests
            const apiBaseUrl = '{api_url}';
            
            // Check if user is logged in
            const idToken = localStorage.getItem('id_token');
            const accessToken = localStorage.getItem('access_token');
            const tokenExpiry = localStorage.getItem('token_expiry');
            
            if (idToken && accessToken) {{
                document.getElementById('login-status').style.display = 'none';
                document.getElementById('user-info').style.display = 'block';
                
                // Enable protected resource buttons
                document.getElementById('load-admin-button').disabled = false;
                
                // Parse the JWT to get user info
                try {{
                    const payload = JSON.parse(atob(idToken.split('.')[1]));
                    document.getElementById('username').textContent = payload.email || payload['cognito:username'];
                    
                    // Format expiry time
                    if (tokenExpiry) {{
                        const expiryDate = new Date(tokenExpiry * 1000);
                        document.getElementById('token-expiry').textContent = expiryDate.toLocaleString();
                    }}
                }} catch (e) {{
                    console.error('Error parsing token', e);
                }}
            }}
            
            // Logout functionality
            document.getElementById('logout-button').addEventListener('click', function() {{
                localStorage.removeItem('id_token');
                localStorage.removeItem('access_token');
                localStorage.removeItem('refresh_token');
                localStorage.removeItem('token_expiry');
                window.location.reload();
            }});
            
            // Load products (public endpoint)
            document.getElementById('load-products-button').addEventListener('click', async function() {{
                const productList = document.getElementById('product-list');
                productList.innerHTML = 'Loading...';
                
                try {{
                    const response = await fetch(apiBaseUrl + 'products');
                    const data = await response.json();
                    
                    productList.innerHTML = '';
                    const promises = data.products.map(async product => {{
                        // Fetch product details for each product immediately
                        try {{
                            const detailResponse = await fetch(apiBaseUrl + `products/${{product.id}}`);
                            const detailData = await detailResponse.json();
                            
                            const productDiv = document.createElement('div');
                            productDiv.className = 'product-card';
                            productDiv.innerHTML = `
                                <h3>${{product.name}}</h3>
                                <p>Price: $${{product.price}}</p>
                                <p>ID: ${{product.id}}</p>
                                <div class="product-details">
                                    <h4>Product Details:</h4>
                                    <p>Description: ${{detailData.description}}</p>
                                    <p>In Stock: ${{detailData.stock}} units</p>
                                    <p>SKU: ${{detailData.sku}}</p>
                                </div>
                            `;
                            productList.appendChild(productDiv);
                        }} catch (e) {{
                            const productDiv = document.createElement('div');
                            productDiv.className = 'product-card';
                            productDiv.innerHTML = `
                                <h3>${{product.name}}</h3>
                                <p>Price: $${{product.price}}</p>
                                <p>ID: ${{product.id}}</p>
                                <div class="product-details">
                                    <p>Error loading details: ${{e.message}}</p>
                                </div>
                            `;
                            productList.appendChild(productDiv);
                        }}
                    }});
                    
                    await Promise.all(promises);
                    productList.style.display = 'block';
                }} catch (e) {{
                    productList.innerHTML = 'Error loading products: ' + e.message;
                }}
            }});
            
            // Load admin content (requires admin group)
            document.getElementById('load-admin-button').addEventListener('click', async function() {{
                const adminResult = document.getElementById('admin-result');
                adminResult.innerHTML = 'Loading admin content...';
                
                try {{
                    const token = localStorage.getItem('id_token');
                    if (!token) {{
                        adminResult.innerHTML = 'You must be logged in to access admin';
                        return;
                    }}
                    
                    const response = await fetch(apiBaseUrl + 'admin', {{
                        headers: {{
                            'Authorization': 'Bearer ' + token
                        }}
                    }});
                    
                    if (!response.ok) {{
                        if (response.status === 403) {{
                            adminResult.innerHTML = 'Access Denied: You do not have admin permissions';
                        }} else {{
                            throw new Error('HTTP Status ' + response.status);
                        }}
                        return;
                    }}
                    
                    const data = await response.json();
                    adminResult.innerHTML = `
                        <h3>Admin Dashboard</h3>
                        <p>${{data.message}}</p>
                    `;
                }} catch (e) {{
                    adminResult.innerHTML = 'Error accessing admin: ' + e.message;
                }}
            }});
        </script>
    </body>
    </html>
    """
    
    return {
        'statusCode': 200,
        'headers': {
            'Content-Type': 'text/html',
            'Access-Control-Allow-Origin': '*'
        },
        'body': html
    }