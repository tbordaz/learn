import json
import os

def handler(event, context):
    """
    Configuration page for the marketplace demo app.
    Contains controls for authentication configuration and admin group management.
    """
    user_pool_id = os.environ.get('USER_POOL_ID')
    client_id = os.environ.get('USER_POOL_CLIENT_ID')
    api_url = os.environ.get('API_URL', '')
    base_url = os.environ.get('BASE_URL', '')
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Marketplace Demo - Configuration</title>
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
                cursor: pointer;
            }}
            .button:hover {{
                background-color: #45a049;
            }}
            .nav-button {{
                display: inline-block;
                background-color: #2196F3;
                color: white;
                padding: 10px 15px;
                text-decoration: none;
                border-radius: 4px;
                margin-bottom: 20px;
            }}
            .nav-button:hover {{
                background-color: #0b7dda;
            }}
            .result-box {{
                padding: 10px;
                margin-top: 10px;
                background-color: #f9f9f9;
                border: 1px solid #ddd;
                border-radius: 4px;
            }}
        </style>
    </head>
    <body>
        <h1>Marketplace Demo Configuration</h1>
        
        <a href="{base_url}/app" class="nav-button">← Back to Main App</a>
        
        <div class="card">
            <h2>Authentication Configuration</h2>
            <div id="auth-config">
                <h3>Make User Admin</h3>
                <p>Add the testuser to the marketplace-admins group:</p>
                <button id="make-admin-button" class="button">Make testuser Admin</button>
                <div id="make-admin-result" class="result-box"></div>
                
                <h3>Authentication Mode</h3>
                <p>Toggle between local Cognito authentication and SAML federation:</p>
                <button id="local-auth-button" class="button">Switch to Local Auth</button>
                <button id="saml-auth-button" class="button">Switch to SAML Auth</button>
                <div id="auth-mode-result" class="result-box"></div>
            </div>
        </div>
        
        <script>
            // Base URLs for API requests
            const apiBaseUrl = '{api_url}';
            
            // Make testuser an admin by adding to marketplace-admins group
            document.getElementById('make-admin-button').addEventListener('click', async function() {{
                const makeAdminResult = document.getElementById('make-admin-result');
                makeAdminResult.innerHTML = 'Making testuser an admin...';
                
                try {{
                    const response = await fetch(apiBaseUrl + 'make-admin', {{
                        method: 'POST',
                        headers: {{
                            'Content-Type': 'application/json'
                        }},
                        body: JSON.stringify({{ username: 'testuser' }})
                    }});
                    
                    const data = await response.json();
                    makeAdminResult.innerHTML = `<p>${{data.message}}</p>`;
                }} catch (e) {{
                    makeAdminResult.innerHTML = 'Error making user admin: ' + e.message;
                }}
            }});
            
            // Switch to local Cognito authentication
            document.getElementById('local-auth-button').addEventListener('click', async function() {{
                const authModeResult = document.getElementById('auth-mode-result');
                authModeResult.innerHTML = 'Switching to local authentication...';
                
                try {{
                    const response = await fetch(apiBaseUrl + 'auth-mode', {{
                        method: 'POST',
                        headers: {{
                            'Content-Type': 'application/json'
                        }},
                        body: JSON.stringify({{ mode: 'local' }})
                    }});
                    
                    const data = await response.json();
                    authModeResult.innerHTML = `
                        <p>${{data.message}}</p>
                        <p>${{data.details}}</p>
                        <p><strong>Current mode:</strong> ${{data.mode}}</p>
                    `;
                }} catch (e) {{
                    authModeResult.innerHTML = 'Error updating authentication mode: ' + e.message;
                }}
            }});
            
            // Switch to SAML authentication with Entra ID
            document.getElementById('saml-auth-button').addEventListener('click', async function() {{
                const authModeResult = document.getElementById('auth-mode-result');
                authModeResult.innerHTML = 'Switching to SAML authentication...';
                
                try {{
                    const response = await fetch(apiBaseUrl + 'auth-mode', {{
                        method: 'POST',
                        headers: {{
                            'Content-Type': 'application/json'
                        }},
                        body: JSON.stringify({{ 
                            mode: 'saml',
                            samlProviderName: 'EntraID'
                        }})
                    }});
                    
                    const data = await response.json();
                    authModeResult.innerHTML = `
                        <p>${{data.message}}</p>
                        <p>${{data.details}}</p>
                        <p><strong>Current mode:</strong> ${{data.mode}}</p>
                    `;
                }} catch (e) {{
                    authModeResult.innerHTML = 'Error updating authentication mode: ' + e.message;
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