import pytest
from unittest.mock import patch, MagicMock
import os
from web import create_app
from flask_login import LoginManager


def test_create_app():
    app = create_app()
    
    # Check app configuration
    assert app.config['SECRET_KEY'] == 'dev'  # Default for testing
    
    # Check Jinja2 extensions
    assert 'jinja2.ext.ExprStmtExtension' in app.jinja_env.extensions
    
    # Check registered blueprints
    assert 'auth' in app.blueprints
    assert 'routes' in app.blueprints


def test_create_app_with_env_secret():
    with patch.dict(os.environ, {'SECRET_KEY': 'test-secret'}):
        app = create_app()
        assert app.config['SECRET_KEY'] == 'test-secret'


def test_app_csrf_protection():
    app = create_app()
    
    # Check CSRF protection is enabled
    assert app.config['WTF_CSRF_ENABLED'] is True
    assert 'csrf' in app.extensions


def test_app_login_manager():
    app = create_app()
    
    # Check login_manager is configured
    assert hasattr(app, 'login_manager')
    assert isinstance(app.login_manager, LoginManager)
    assert app.login_manager.login_view == 'auth.login'
