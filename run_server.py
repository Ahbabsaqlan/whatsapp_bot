from flask import Flask
from api_routes import api  
import database_manager as db

app = Flask(__name__)

app.register_blueprint(api, url_prefix='/api')

if __name__ == '__main__':
    db.init_db()
    app.run(host='0.0.0.0', port=5001, debug=True)