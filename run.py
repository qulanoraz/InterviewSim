# Application entry point 
from dotenv import load_dotenv
load_dotenv()

import os
import sys

print("DEBUG: current working dir:", os.getcwd())
print("DEBUG: sys.path[0]:", sys.path[0])
print("DEBUG: .env exists:", os.path.exists(os.path.join(os.getcwd(), '.env')))

load_dotenv()
print("DEBUG after load_dotenv:", os.environ.get("DEEPGRAM_API_KEY"))


from app import create_app

# Load environment-specific configuration or default to 'development'
# The FLASK_CONFIG environment variable can be set to 'testing' or 'production'
# In a production environment, you would typically use a WSGI server like Gunicorn
# and set FLASK_CONFIG accordingly, or pass it to create_app directly.
config_name = os.getenv('FLASK_CONFIG') or 'default' 
app = create_app(config_name)   

if __name__ == '__main__':
    # The Flask development server is not suitable for production.
    # Use a production WSGI server like Gunicorn or uWSGI for deployment.
    # Example: gunicorn -w 4 -b 0.0.0.0:5000 "run:app"
    
    # For development, app.run() is fine.
    # Debug mode is typically enabled via FLASK_DEBUG=1 environment variable
    # or by setting app.debug = True (which DevelopmentConfig does).
    # host='0.0.0.0' makes the server accessible externally (e.g., within a Docker container or LAN)
    # port can be configured as needed.
    print(f"Starting Flask app with '{config_name}' configuration...")
    print(f"Debug mode: {app.debug}")
    print(f"Registered Blueprints: {list(app.blueprints.keys())}")
    print(f"Available routes:")
    for rule in app.url_map.iter_rules():
        print(f"  {rule.endpoint}: {rule.rule} ({ ', '.join(rule.methods) })")
    
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000))) 