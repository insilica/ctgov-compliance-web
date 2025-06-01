import os
from flask import Flask
from flask_wtf import CSRFProtect
from .auth import bp as auth_bp, login_manager
from .dashboard import bp as dashboard_bp

csrf = CSRFProtect()


def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev')

    csrf.init_app(app)

    login_manager.init_app(app)
    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)

    return app
