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

# Determine the configuration based on FLASK_CONFIG environment variable
# Defaults to 'development' if not set.
config_name = os.getenv('FLASK_CONFIG', 'development')
app = create_app(config_name)

if __name__ == '__main__':
    # Runs the Flask development server
    # host='0.0.0.0' makes the server accessible externally (e.g., from a VM or other devices on the same network)
    # port=5001 ensures it runs on the port Vite is proxying to
    # debug=True enables the Flask debugger and reloader, very useful for development
    print(f"Starting Flask app with '{config_name}' config on host 0.0.0.0, port 5001, debug=True")
    app.run(host='0.0.0.0', port=5001, debug=True) 