import os
from web import create_app


def test_create_app_registers_blueprints(monkeypatch):
    os.environ['SECRET_KEY'] = 'test-secret'
    app = create_app()
    assert app.config['SECRET_KEY'] == 'test-secret'
    assert 'auth.login' in app.view_functions
    assert 'dashboard.index' in app.view_functions
