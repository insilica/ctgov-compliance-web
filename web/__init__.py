import os
from flask import Flask
from flask_wtf import CSRFProtect
from .auth import bp as auth_bp, login_manager
from .routes import bp as routes_bp

csrf = CSRFProtect()


def create_app(test_config=None):
    app = Flask(__name__)
    
    # Load default configuration
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev')
    
    # Override with test config if provided
    if test_config is not None:
        app.config.update(test_config)
    
    # Add Jinja2 extensions
    app.jinja_env.add_extension('jinja2.ext.do')

    csrf.init_app(app)

    login_manager.init_app(app)
    app.register_blueprint(auth_bp)
    app.register_blueprint(routes_bp)

    return app
