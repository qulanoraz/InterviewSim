from flask import Flask
from config import config
import os

# If you have extensions like SQLAlchemy, LoginManager, etc., initialize them here
# from flask_sqlalchemy import SQLAlchemy
# from flask_login import LoginManager
# db = SQLAlchemy()
# login_manager = LoginManager()
# login_manager.login_view = 'auth.login' # Example for Flask-Login

def create_app(config_name=None):
    if config_name is None:
        config_name = os.getenv('FLASK_CONFIG', 'default')

    app = Flask(__name__)
    app.config.from_object(config[config_name])
    config[config_name].init_app(app) # Call init_app on the config object itself

    # Initialize extensions with the app instance
    # db.init_app(app)
    # login_manager.init_app(app)

    # Register blueprints
    from .api.routes import api_bp as api_blueprint
    app.register_blueprint(api_blueprint, url_prefix='/api') # All api routes will be under /api

    # You can add a simple route here for testing if the app is running
    @app.route('/hello')
    def hello():
        return 'Hello, World from JobSim AI Backend!'

    return app 