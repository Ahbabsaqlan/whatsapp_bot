from flask import Flask
from api_routes import app as api_app
from lawyer_api_routes import lawyer_api
import database_manager as db
import lawyer_directory_integration as ldi

app = Flask(__name__)

# Register the lawyer directory API routes
app.register_blueprint(lawyer_api, url_prefix='/api/lawyer')

# Copy routes from api_routes.app to this app
for rule in api_app.url_map.iter_rules():
    if rule.endpoint != 'static':
        app.add_url_rule(
            rule.rule,
            endpoint=rule.endpoint,
            view_func=api_app.view_functions[rule.endpoint],
            methods=rule.methods
        )

if __name__ == '__main__':
    db.init_db()
    ldi.init_lawyer_directory_db()
    app.run(host='0.0.0.0', port=5001, debug=True)