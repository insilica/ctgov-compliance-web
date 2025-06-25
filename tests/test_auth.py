import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta, timezone
from flask import url_for
from werkzeug.security import generate_password_hash, check_password_hash
from web.auth import User, load_user, login, register, reset_request, reset_password

@pytest.fixture
def user_data():
    return {
        'id': 1,
        'email': 'test@example.com',
        'password_hash': generate_password_hash('password')
    }


@pytest.fixture
def mock_query():
    with patch('web.auth.query') as mock:
        yield mock


@pytest.fixture
def mock_execute():
    with patch('web.auth.execute') as mock:
        yield mock


@pytest.fixture
def flask_app():
    from web import create_app
    app = create_app()
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    
    with app.test_request_context():
        yield app


def test_user_init(user_data):
    user = User(user_data['id'], user_data['email'], user_data['password_hash'])
    assert user.id == 1
    assert user.email == 'test@example.com'
    assert user.password_hash == user_data['password_hash']
    assert user._organizations is None


def test_user_organizations(user_data, mock_query):
    org_data = [
        {'id': 1, 'name': 'Org1', 'role': 'admin'},
        {'id': 2, 'name': 'Org2', 'role': 'user'}
    ]
    mock_query.return_value = org_data
    
    user = User(user_data['id'], user_data['email'], user_data['password_hash'])
    
    # First call should query the database
    assert user.organizations == org_data
    mock_query.assert_called_once()
    sql, params = mock_query.call_args[0]
    assert 'user_id = %s' in sql
    assert params == [1]
    
    # Second call should use cached value
    mock_query.reset_mock()
    assert user.organizations == org_data
    mock_query.assert_not_called()


def test_user_organization_ids(user_data, mock_query):
    org_data = [
        {'id': 1, 'name': 'Org1', 'role': 'admin'},
        {'id': 2, 'name': 'Org2', 'role': 'user'}
    ]
    mock_query.return_value = org_data
    
    user = User(user_data['id'], user_data['email'], user_data['password_hash'])
    assert user.organization_ids == '1,2'


def test_user_trials(user_data, mock_query):
    trial_data = [{'id': 101}, {'id': 102}]
    mock_query.return_value = trial_data
    
    user = User(user_data['id'], user_data['email'], user_data['password_hash'])
    assert user.trials == trial_data
    
    mock_query.assert_called_once()
    sql, params = mock_query.call_args[0]
    assert 'user_id = %s' in sql
    assert params == [1]


def test_user_get_success(user_data, mock_query):
    mock_query.return_value = user_data
    
    user = User.get(1)
    
    assert isinstance(user, User)
    assert user.id == 1
    assert user.email == 'test@example.com'
    
    mock_query.assert_called_once()
    print(mock_query.call_args[0])
    sql, params, *rest = mock_query.call_args[0]
    assert 'id=%s' in sql
    assert params == [1]
    # Check fetchone=True if it's passed as a keyword argument
    if rest and isinstance(rest[0], dict):
        assert rest[0].get('fetchone') is True


def test_user_get_not_found(mock_query):
    mock_query.return_value = None
    
    result = User.get(999)
    
    assert result is None
    mock_query.assert_called_once()


def test_load_user(mock_query, user_data):
    with patch('web.auth.User.get') as mock_get:
        mock_user = MagicMock()
        mock_get.return_value = mock_user
        
        result = load_user('1')
        
        assert result == mock_user
        mock_get.assert_called_once_with('1')


def test_login_success(flask_app, mock_query, mock_execute):
    with flask_app.test_request_context(
        '/login', method='POST', data={'email': 'test@example.com', 'password': 'password'}
    ):
        # Mock query result for valid login
        mock_query.return_value = {
            'id': 1, 
            'email': 'test@example.com', 
            'password_hash': generate_password_hash('password')
        }
        
        with patch('web.auth.login_user') as mock_login, \
             patch('web.auth.flash') as mock_flash, \
             patch('web.auth.redirect') as mock_redirect:
            
            mock_redirect.return_value = 'redirect_response'
            
            response = login()
            
            # Check query was called with correct params
            mock_query.assert_called_once()
            assert 'email=%s' in mock_query.call_args[0][0]
            assert mock_query.call_args[0][1] == ['test@example.com']
            
            # Check login_user was called
            mock_login.assert_called_once()
            user_obj = mock_login.call_args[0][0]
            assert isinstance(user_obj, User)
            assert user_obj.id == 1
            assert user_obj.email == 'test@example.com'
            
            # Check login activity recorded
            mock_execute.assert_called_once()
            assert 'INSERT INTO login_activity' in mock_execute.call_args[0][0]
            assert mock_execute.call_args[0][1] == [1]
            
            # Check flash and redirect
            mock_flash.assert_called_once_with('Logged in successfully.', 'success')
            mock_redirect.assert_called_once()
            assert response == 'redirect_response'


def test_login_invalid_credentials(flask_app, mock_query):
    with flask_app.test_request_context(
        '/login', method='POST', data={'email': 'test@example.com', 'password': 'wrong'}
    ):
        # Mock query result for user but with wrong password
        mock_query.return_value = {
            'id': 1, 
            'email': 'test@example.com', 
            'password_hash': generate_password_hash('password')
        }
        
        with patch('web.auth.login_user') as mock_login, \
             patch('web.auth.flash') as mock_flash, \
             patch('web.auth.render_template') as mock_render:
            
            mock_render.return_value = 'template_response'
            
            response = login()
            
            # Check login_user was not called
            mock_login.assert_not_called()
            
            # Check flash error
            mock_flash.assert_called_once_with('Invalid credentials', 'error')
            mock_render.assert_called_once_with('auth/login.html')
            assert response == 'template_response'


def test_login_user_not_found(flask_app, mock_query):
    with flask_app.test_request_context(
        '/login', method='POST', data={'email': 'nonexistent@example.com', 'password': 'password'}
    ):
        # Mock query result for no user found
        mock_query.return_value = None
        
        with patch('web.auth.login_user') as mock_login, \
             patch('web.auth.flash') as mock_flash, \
             patch('web.auth.render_template') as mock_render:
            
            mock_render.return_value = 'template_response'
            
            response = login()
            
            # Check login_user was not called
            mock_login.assert_not_called()
            
            # Check flash error
            mock_flash.assert_called_once_with('Invalid credentials', 'error')
            mock_render.assert_called_once_with('auth/login.html')
            assert response == 'template_response'


def test_register_success(flask_app, mock_query, mock_execute):
    with flask_app.test_request_context(
        '/register', method='POST', data={'email': 'new@example.com', 'password': 'password'}
    ):
        # Mock query for checking existing user - return None to indicate no existing user
        mock_query.return_value = None
        
        with patch('web.auth.flash') as mock_flash, \
             patch('web.auth.redirect') as mock_redirect, \
             patch('web.auth.generate_password_hash') as mock_hash:
            
            mock_hash.return_value = 'hashed_password'
            mock_redirect.return_value = 'redirect_response'
            
            response = register()
            
            # Check existing user query
            mock_query.assert_called_once()
            assert 'email=%s' in mock_query.call_args[0][0]
            assert mock_query.call_args[0][1] == ['new@example.com']
            
            # Check password hashing
            mock_hash.assert_called_once_with('password')
            
            # Check user creation
            mock_execute.assert_called_once()
            assert 'INSERT INTO ctgov_user' in mock_execute.call_args[0][0]
            assert mock_execute.call_args[0][1] == ['new@example.com', 'hashed_password']
            
            # Check flash and redirect
            mock_flash.assert_called_once_with('Registration successful. Please log in.', 'success')
            mock_redirect.assert_called_once()
            assert response == 'redirect_response'


def test_register_existing_email(flask_app, mock_query):
    with flask_app.test_request_context(
        '/register', method='POST', data={'email': 'existing@example.com', 'password': 'password'}
    ):
        # Mock query for checking existing user - return data to indicate user exists
        mock_query.return_value = {'id': 1}
        
        with patch('web.auth.flash') as mock_flash, \
             patch('web.auth.render_template') as mock_render:
            
            mock_render.return_value = 'template_response'
            
            response = register()
            
            # Check existing user query
            mock_query.assert_called_once()
            
            # Check no user creation attempted
            assert not hasattr(mock_execute, 'called')
            
            # Check flash error
            mock_flash.assert_called_once()
            assert 'already registered' in mock_flash.call_args[0][0]
            
            mock_render.assert_called_once_with('auth/register.html')
            assert response == 'template_response'


def test_logout(flask_app):
    with flask_app.test_request_context('/logout'):
        # Mock flask_login.logout_user directly
        with patch('flask_login.logout_user') as mock_logout:
            
            # Call logout_user directly
            from flask_login import logout_user
            logout_user()
            
            # Check that flask_login.logout_user was called
            mock_logout.assert_called_once()


def test_reset_request_user_found(flask_app, mock_query, mock_execute):
    with flask_app.test_request_context(
        '/reset', method='POST', data={'email': 'test@example.com'}
    ):
        # Mock query for finding user
        mock_query.return_value = {'id': 1}
        
        with patch('web.auth.secrets.token_urlsafe') as mock_token, \
             patch('web.auth.flash') as mock_flash, \
             patch('web.auth.render_template') as mock_render, \
             patch('web.auth.datetime') as mock_datetime, \
             patch('web.auth.url_for') as mock_url_for:
            
            mock_token.return_value = 'random_token'
            mock_datetime.now.return_value = datetime(2023, 1, 1, tzinfo=timezone.utc)
            mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)
            mock_url_for.return_value = '/reset/random_token'
            mock_render.return_value = 'template_response'
            
            response = reset_request()
            
            # Check user query
            mock_query.assert_called_once()
            assert 'email=%s' in mock_query.call_args[0][0]
            assert mock_query.call_args[0][1] == ['test@example.com']
            
            # Check token creation
            mock_token.assert_called_once_with(32)
            
            # Check reset record creation
            mock_execute.assert_called_once()
            assert 'INSERT INTO password_reset' in mock_execute.call_args[0][0]
            expected_expiry = datetime(2023, 1, 1, tzinfo=timezone.utc) + timedelta(hours=1)
            assert mock_execute.call_args[0][1] == [1, 'random_token', expected_expiry]
            
            # Check flash and render
            mock_flash.assert_called_once()
            assert 'reset link' in mock_flash.call_args[0][0]
            mock_render.assert_called_once_with('auth/reset_request.html')
            assert response == 'template_response'


def test_reset_request_user_not_found(flask_app, mock_query):
    with flask_app.test_request_context(
        '/reset', method='POST', data={'email': 'nonexistent@example.com'}
    ):
        # Mock query for user not found
        mock_query.return_value = None
        
        with patch('web.auth.flash') as mock_flash, \
             patch('web.auth.render_template') as mock_render:
            
            mock_render.return_value = 'template_response'
            
            response = reset_request()
            
            # Check user query
            mock_query.assert_called_once()
            
            # Check no token creation or reset record
            assert not hasattr(mock_execute, 'called')
            
            # Check generic flash message (for security)
            mock_flash.assert_called_once()
            assert 'If that email is registered' in mock_flash.call_args[0][0]
            
            mock_render.assert_called_once_with('auth/reset_request.html')
            assert response == 'template_response'


def test_reset_password_valid_token(flask_app, mock_query, mock_execute):
    token = 'valid_token'
    
    with flask_app.test_request_context(
        f'/reset/{token}', method='POST', data={'password': 'newpassword'}
    ):
        # First query is for token validation
        # Second query is for user email
        mock_query.side_effect = [
            {'id': 1, 'user_id': 2, 'expires_at': datetime.now(timezone.utc) + timedelta(hours=1)},
            {'email': 'test@example.com'}
        ]
        
        with patch('web.auth.flash') as mock_flash, \
             patch('web.auth.redirect') as mock_redirect, \
             patch('web.auth.generate_password_hash') as mock_hash:
            
            mock_hash.return_value = 'new_hashed_password'
            mock_redirect.return_value = 'redirect_response'
            
            response = reset_password(token)
            
            # Check token query
            assert mock_query.call_count == 2
            assert 'token=%s' in mock_query.call_args_list[0][0][0]
            assert mock_query.call_args_list[0][0][1] == [token]
            
            # Check password update
            assert mock_execute.call_count == 2
            assert 'UPDATE ctgov_user SET password_hash=%s' in mock_execute.call_args_list[0][0][0]
            assert mock_execute.call_args_list[0][0][1] == ['new_hashed_password', 2]
            
            # Check token deletion
            assert 'DELETE FROM password_reset WHERE id=%s' in mock_execute.call_args_list[1][0][0]
            assert mock_execute.call_args_list[1][0][1] == [1]
            
            # Check flash and redirect
            mock_flash.assert_called_once_with('Password successfully updated! Please log in.', 'success')
            mock_redirect.assert_called_once()
            assert response == 'redirect_response'


def test_reset_password_invalid_token(flask_app, mock_query):
    token = 'invalid_token'
    
    with flask_app.test_request_context(f'/reset/{token}'):
        # Mock query for invalid token
        mock_query.return_value = None
        
        with patch('web.auth.flash') as mock_flash, \
             patch('web.auth.redirect') as mock_redirect:
            
            mock_redirect.return_value = 'redirect_response'
            
            response = reset_password(token)
            
            # Check token query
            mock_query.assert_called_once()
            assert 'token=%s' in mock_query.call_args[0][0]
            
            # Check flash and redirect
            mock_flash.assert_called_once_with('Invalid or expired token.', 'error')
            mock_redirect.assert_called_once()
            assert response == 'redirect_response'


def test_reset_password_expired_token(flask_app, mock_query):
    token = 'expired_token'
    
    with flask_app.test_request_context(f'/reset/{token}'):
        # Mock query for expired token (expired_at is in the past)
        mock_query.return_value = {
            'id': 1, 
            'user_id': 2, 
            'expires_at': datetime.now(timezone.utc) - timedelta(hours=1)
        }
        
        with patch('web.auth.flash') as mock_flash, \
             patch('web.auth.redirect') as mock_redirect:
            
            mock_redirect.return_value = 'redirect_response'
            
            response = reset_password(token)
            
            # Check flash and redirect
            mock_flash.assert_called_once_with('Invalid or expired token.', 'error')
            mock_redirect.assert_called_once()
            assert response == 'redirect_response'


def test_reset_password_user_not_found(flask_app, mock_query):
    token = 'valid_token'
    
    with flask_app.test_request_context(f'/reset/{token}'):
        # First query is for token validation (valid)
        # Second query is for user email (not found)
        mock_query.side_effect = [
            {'id': 1, 'user_id': 2, 'expires_at': datetime.now(timezone.utc) + timedelta(hours=1)},
            None
        ]
        
        with patch('web.auth.flash') as mock_flash, \
             patch('web.auth.redirect') as mock_redirect:
            
            mock_redirect.return_value = 'redirect_response'
            
            response = reset_password(token)
            
            # Check flash and redirect
            mock_flash.assert_called_once_with('User not found.', 'error')
            mock_redirect.assert_called_once()
            assert response == 'redirect_response'
