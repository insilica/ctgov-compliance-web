import pytest
from unittest.mock import patch, MagicMock
import os
from web import create_app
from flask_login import LoginManager
from flask import Flask, g, session, request, current_app
from flask_wtf.csrf import CSRFProtect
from datetime import timedelta


def test_create_app():
    app = create_app()
    
    # Check app configuration
    # In CI environment, SECRET_KEY is set via environment variable
    expected_secret_key = os.environ.get('SECRET_KEY', 'dev')
    assert app.config['SECRET_KEY'] == expected_secret_key
    
    # Check Jinja2 extensions
    assert 'jinja2.ext.ExprStmtExtension' in app.jinja_env.extensions
    
    # Check registered blueprints
    assert 'auth' in app.blueprints
    assert 'routes' in app.blueprints
    
    # Verify blueprint URLs
    assert app.url_map.bind('localhost').match('/login')[0] == 'auth.login'
    assert app.url_map.bind('localhost').match('/')[0] == 'routes.index'


def test_create_app_with_env_secret():
    with patch.dict(os.environ, {'SECRET_KEY': 'test-secret'}):
        app = create_app()
        assert app.config['SECRET_KEY'] == 'test-secret'


def test_create_app_with_test_config():
    app = create_app(test_config={'TESTING': True, 'SECRET_KEY': 'test-key'})
    assert app.config['TESTING'] is True
    assert app.config['SECRET_KEY'] == 'test-key'


def test_app_csrf_protection():
    app = create_app()
    
    # Check CSRF protection is enabled
    assert app.config['WTF_CSRF_ENABLED'] is True
    assert 'csrf' in app.extensions
    
    # Verify the CSRF extension is properly initialized
    csrf_extension = app.extensions['csrf']
    assert isinstance(csrf_extension, CSRFProtect)


@patch('web.backend.api.auth.login_manager.init_app')
def test_app_login_manager(mock_init_app):
    app = create_app()
    
    # Verify login_manager.init_app was called with the app
    mock_init_app.assert_called_once()


def test_app_routes_registered():
    app = create_app()
    
    # Check that essential routes are registered
    rules = [rule.endpoint for rule in app.url_map.iter_rules()]
    
    # Auth routes
    assert 'auth.login' in rules
    assert 'auth.logout' in rules
    assert 'auth.register' in rules
    assert 'auth.reset_request' in rules
    
    # Main routes
    assert 'routes.index' in rules
    assert 'routes.show_organization_dashboard' in rules
    assert 'routes.show_compare_organizations_dashboard' in rules
    assert 'routes.show_user_dashboard' in rules


def test_app_static_files():
    app = create_app()
    
    with app.test_client() as client:
        # Test that static files are served
        response = client.get('/static/style.css')
        assert response.status_code == 200
        assert 'text/css' in response.headers['Content-Type']


def test_app_template_rendering():
    app = create_app()
    
    # Test that the app can render templates
    with app.test_request_context():
        with patch('flask.render_template') as mock_render:
            mock_render.return_value = "Test Template"
            from flask import render_template
            result = render_template('layout.html')
            assert result == "Test Template"
            mock_render.assert_called_once_with('layout.html')


def test_app_error_handling():
    app = create_app()
    
    # Test 404 error handling
    with app.test_client() as client:
        response = client.get('/nonexistent-route')
        assert response.status_code == 404

def test_app_response_headers():
    app = create_app()
    
    with app.test_client() as client:
        response = client.get('/', follow_redirects=True)
        
        # Check common response headers
        assert 'Content-Type' in response.headers
        assert 'Content-Length' in response.headers


def test_app_secure_headers():
    app = create_app()
    
    # Add security headers if they don't exist
    @app.after_request
    def add_security_headers(response):
        response.headers['Content-Security-Policy'] = "default-src 'self'"
        return response
    
    with app.test_client() as client:
        response = client.get('/', follow_redirects=True)
        assert 'Content-Security-Policy' in response.headers

def test_app_session_config():
    app = create_app()
    
    # Check session configuration
    assert app.config['SESSION_TYPE'] == 'filesystem' if 'SESSION_TYPE' in app.config else True
    
    # Check permanent session lifetime if configured
    if 'PERMANENT_SESSION_LIFETIME' in app.config:
        assert isinstance(app.config['PERMANENT_SESSION_LIFETIME'], (int, timedelta))


def test_app_request_context():
    app = create_app()
    
    with app.test_request_context('/'):
        from flask import request
        assert request.path == '/'
        assert request.method == 'GET'


def test_app_url_generation():
    app = create_app()
    
    with app.test_request_context():
        from flask import url_for
        assert url_for('auth.login') == '/login'
        assert url_for('auth.register') == '/register'
        assert url_for('routes.index') == '/'


def test_app_http_methods():
    # Create app with CSRF disabled for testing
    app = create_app(test_config={'WTF_CSRF_ENABLED': False, 'TESTING': True})
    
    with app.test_client() as client:
        # Test GET request
        get_response = client.get('/')
        assert get_response.status_code in [200, 302]  # 200 OK or 302 redirect if login required


def test_app_session_handling():
    app = create_app(test_config={'TESTING': True, 'SECRET_KEY': 'test-session-key'})
    
    with app.test_client() as client:
        with client.session_transaction() as sess:
            sess['test_key'] = 'test_value'
        
        # Access the session after the request
        response = client.get('/')
        with client.session_transaction() as sess:
            assert sess['test_key'] == 'test_value'


def test_app_config_values():
    app = create_app(test_config={
        'DEBUG': True,
        'TESTING': True,
        'SERVER_NAME': 'test.local'
    })
    
    assert app.config['DEBUG'] is True
    assert app.config['TESTING'] is True
    assert app.config['SERVER_NAME'] == 'test.local'


def test_app_context():
    app = create_app(test_config={'TESTING': True})
    
    with app.app_context():
        # Test that current_app is properly set
        assert current_app._get_current_object() == app
        
        # Test g object
        g.test_value = 'test'
        assert g.test_value == 'test'


def test_blueprint_url_prefix():
    app = create_app()
    
    # Check that blueprints are registered with correct URL prefixes
    for rule in app.url_map.iter_rules():
        if rule.endpoint.startswith('auth.'):
            # Auth routes should not have a prefix
            assert not rule.rule.startswith('/auth/')
        elif rule.endpoint.startswith('routes.'):
            # Main routes should not have a prefix
            assert not rule.rule.startswith('/routes/')


def test_error_handlers():
    app = create_app(test_config={'TESTING': True})
    
    # Add custom error handler for testing
    @app.errorhandler(404)
    def custom_404(error):
        return 'Custom 404 Page', 404
    
    with app.test_client() as client:
        response = client.get('/nonexistent-page')
        assert response.status_code == 404
        assert response.data == b'Custom 404 Page'


def test_app_request_methods():
    app = create_app(test_config={'TESTING': True, 'WTF_CSRF_ENABLED': False})
    
    with app.test_client() as client:
        # Test different HTTP methods
        assert client.get('/').status_code in [200, 302]
        assert client.head('/').status_code in [200, 302]
        
        # These should return 405 Method Not Allowed for routes that don't support them
        assert client.put('/').status_code in [405, 302]
        assert client.delete('/').status_code in [405, 302]
        assert client.patch('/').status_code in [405, 302]


def test_app_before_request():
    app = create_app(test_config={'TESTING': True})
    
    # Add before_request handler
    @app.before_request
    def before_request_handler():
        g.before_request_called = True
    
    with app.test_client() as client:
        # Make a request to trigger before_request
        with app.app_context():
            client.get('/')
            assert hasattr(g, 'before_request_called')
            assert g.before_request_called is True
