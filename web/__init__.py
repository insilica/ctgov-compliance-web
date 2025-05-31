import os
from flask import Flask
from .auth import bp as auth_bp, login_manager
from .dashboard import bp as dashboard_bp


def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev')

    login_manager.init_app(app)
    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)

    return app
