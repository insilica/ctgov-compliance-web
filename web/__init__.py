import os
from flask import Flask, request, g
from flask_wtf import CSRFProtect
from flask_login import current_user, login_user
from .auth import bp as auth_bp, login_manager
from .routes import bp as routes_bp
from .telemetry import init_telemetry, instrument_flask_app

csrf = CSRFProtect()


def create_app(test_config=None):
    app = Flask(__name__)
    
    # Load default configuration
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev')
    app.config['ENVIRONMENT'] = os.environ.get('ENVIRONMENT', 'production')
    
    # Override with test config if provided
    if test_config is not None:
        app.config.update(test_config)
    
    # Initialize OpenTelemetry before registering blueprints
    init_telemetry()
    instrument_flask_app(app)
    
    # Add Jinja2 extensions
    app.jinja_env.add_extension('jinja2.ext.do')

    csrf.init_app(app)

    login_manager.init_app(app)
    app.register_blueprint(auth_bp)
    app.register_blueprint(routes_bp)

    # Auto-authentication for development and preview environments
    @app.before_request
    def auto_authenticate_dev_user():
        # Only auto-authenticate in dev and preview environments
        if app.config.get('ENVIRONMENT') not in ['dev', 'preview']:
            return
        
        # Skip auto-auth for auth routes and health check
        if request.endpoint in ['auth.login', 'auth.register', 'auth.logout', 'auth.reset_request', 'auth.reset_password', 'routes.health']:
            return
            
        # Skip if user is already authenticated
        if current_user.is_authenticated:
            return
            
        # Auto-login as default test user
        try:
            from .auth import User
            user = User.get_by_email('user1@example.com')
            if user:
                login_user(user)
                app.logger.info(f"Auto-authenticated user: {user.email} (dev environment)")
        except Exception as e:
            # If auto-authentication fails, let normal auth flow handle it
            app.logger.warning(f"Auto-authentication failed: {e}")

    return app
