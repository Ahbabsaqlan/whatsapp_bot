# run_server.py

from flask import Flask
from api_routes import api  # Import the Blueprint from our routes file
import database_manager as db

# Create the main Flask application instance
app = Flask(__name__)

# Register the Blueprint. All routes from api_routes.py will now be active.
# We add a URL prefix to keep our API organized. All routes will start with /api/...
app.register_blueprint(api, url_prefix='/api')

if __name__ == '__main__':
    # Ensure the database and its tables exist before starting the server.
    db.init_db()
    
    # Run the Flask app. 
    # port=5001 is used to avoid conflicts on macOS. You can change it.
    # host='0.0.0.0' makes the server accessible from other devices on your network.
    app.run(host='0.0.0.0', port=5001, debug=True)