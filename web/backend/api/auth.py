from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import LoginManager, login_user, logout_user, login_required, UserMixin, current_user
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import datetime, timedelta, timezone
import secrets
from ..repositories.db import query, execute
from opentelemetry import trace
from ..extensions import csrf

tracer = trace.get_tracer(__name__)

bp = Blueprint('auth', __name__)
login_manager = LoginManager()
login_manager.login_view = 'auth.login'


class User(UserMixin):
    def __init__(self, id_, email, password_hash):
        self.id = id_
        self.email = email
        self.password_hash = password_hash
        self._organizations = None

    @property
    @tracer.start_as_current_span("auth.user.organizations")
    def organizations(self):
        current_span = trace.get_current_span()

        sql = '''
            SELECT o.id, o.name, uo.role 
            FROM organization o 
            JOIN user_organization uo ON o.id = uo.organization_id 
            WHERE uo.user_id = %s
        '''

        current_span.set_attribute("sql", sql)
        current_span.set_attribute("[self.id]", [self.id])
        if self._organizations is None:
            rows = query(sql, [self.id])
            self._organizations = rows
        current_span.set_attribute("self._organizations", str(self._organizations))
        return self._organizations

    @property
    def organization_ids(self):
        return ','.join(str(org['id']) for org in self.organizations)
    
    @property
    @tracer.start_as_current_span("auth.user.trials")
    def trials(self):
        return query('SELECT id FROM trial WHERE user_id = %s', [self.id])

    @staticmethod
    @tracer.start_as_current_span("auth.user.get")
    def get(user_id):
        current_span = trace.get_current_span()
        current_span.set_attribute("user_id", user_id)

        sql = 'SELECT id, email, password_hash FROM ctgov_user WHERE id=%s'

        current_span.set_attribute("sql", sql)

        row = query(sql, [user_id], fetchone=True)
        if row:
            return User(row['id'], row['email'], row['password_hash'])
        return None

    @staticmethod
    @tracer.start_as_current_span("auth.user.get_by_email")
    def get_by_email(email):
        current_span = trace.get_current_span()
        current_span.set_attribute("user.email_length", len(email) if email else 0)
        row = query('SELECT id, email, password_hash FROM ctgov_user WHERE email=%s', [email], fetchone=True)
        if row:
            return User(row['id'], row['email'], row['password_hash'])
        return None

@login_manager.user_loader
def load_user(user_id):
    return User.get(user_id)


@bp.route('/login', methods=['GET', 'POST'])
@tracer.start_as_current_span("auth.login")
def login():
    current_span = trace.get_current_span()
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        current_span.set_attribute("user.email_length", len(email) if email else 0)
        row = query('SELECT id, email, password_hash FROM ctgov_user WHERE email=%s', [email], fetchone=True)
        if row and check_password_hash(row['password_hash'], password):
            user = User(row['id'], row['email'], row['password_hash'])
            login_user(user)
            execute('INSERT INTO login_activity (user_id) VALUES (%s)', [user.id])
            flash('Logged in successfully.', 'success')
            return redirect(url_for('routes.index'))
        flash('Invalid credentials', 'error')
    return render_template('auth/login.html')


@bp.route('/register', methods=['GET', 'POST'])
@tracer.start_as_current_span("auth.register")
def register():
    current_span = trace.get_current_span()
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        current_span.set_attribute("user.email_length", len(email) if email else 0)
        existing = query('SELECT id FROM ctgov_user WHERE email=%s', [email], fetchone=True)
        
        if existing:
            flash('The email address, ' + email + ', is already registered. <a href="/reset" class="usa-link">Reset your password</a>', 'error')
        else:
            password_hash = generate_password_hash(password)
            # First create the user
            execute(
                'INSERT INTO ctgov_user (email, password_hash) VALUES (%s, %s) RETURNING id',
                [email, password_hash],
            )
            
            flash('Registration successful. Please log in.', 'success')
            return redirect(url_for('auth.login'))
    return render_template('auth/register.html')


@bp.route('/logout')
@login_required    # pragma: no cover
@tracer.start_as_current_span("auth.logout")
def logout():
    logout_user()
    return redirect(url_for('auth.login'))


@bp.route('/reset', methods=['GET', 'POST'])
@tracer.start_as_current_span("auth.reset_request")
def reset_request():
    current_span = trace.get_current_span()
    if request.method == 'POST':
        email = request.form['email']
        current_span.set_attribute("user.email_length", len(email) if email else 0)
        user = query('SELECT id FROM ctgov_user WHERE email=%s', [email], fetchone=True)
        if user:
            token = secrets.token_urlsafe(32)
            expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
            execute(
                'INSERT INTO password_reset (user_id, token, expires_at) VALUES (%s, %s, %s)',
                [user['id'], token, expires_at],
            )
            flash(
                f'Password reset link: {url_for("auth.reset_password", token=token, _external=True)}',
                'info',
            )
        else:
            flash('If that email is registered, a reset link has been generated.', 'info')
    return render_template('auth/reset_request.html')


@bp.route('/reset/<token>', methods=['GET', 'POST'])
@tracer.start_as_current_span("auth.reset_password")
def reset_password(token):
    current_span = trace.get_current_span()
    row = query('SELECT id, user_id, expires_at FROM password_reset WHERE token=%s', [token], fetchone=True)
    if not row or row['expires_at'] < datetime.now(timezone.utc):
        flash('Invalid or expired token.', 'error')
        return redirect(url_for('auth.reset_request'))
    
    # Get user's email
    user = query('SELECT email FROM ctgov_user WHERE id=%s', [row['user_id']], fetchone=True)
    if not user:
        flash('User not found.', 'error')
        return redirect(url_for('auth.reset_request'))
        
    if request.method == 'POST':
        password = request.form['password']
        password_hash = generate_password_hash(password)
        execute('UPDATE ctgov_user SET password_hash=%s WHERE id=%s', [password_hash, row['user_id']])
        execute('DELETE FROM password_reset WHERE id=%s', [row['id']])
        flash('Password successfully updated! Please log in.', 'success')
        return redirect(url_for('auth.login'))
    return render_template('auth/reset_password.html', email=user['email'])


def _serialize_user(user: User):
    orgs = []
    for org in user.organizations:
        item = dict(org)
        orgs.append(
            {
                'id': item['id'],
                'name': item['name'],
                'role': item.get('role'),
            }
        )
    roles = [org['role'] for org in orgs if org.get('role')]
    return {
        'id': user.id,
        'email': user.email,
        'name': user.email.split('@')[0],
        'roles': roles,
        'organizations': orgs,
    }


def _complete_login(user: User):
    login_user(user)
    execute('INSERT INTO login_activity (user_id) VALUES (%s)', [user.id])


@bp.route('/api/auth/login', methods=['POST'])
@csrf.exempt
@tracer.start_as_current_span("auth.api_login")
def api_login():
    if not request.is_json:
        return jsonify({'message': 'Expected JSON body.'}), 400

    payload = request.get_json(silent=True) or {}
    email = (payload.get('email') or '').strip()
    password = payload.get('password') or ''
    if not email or not password:
        return jsonify({'message': 'Email and password are required.'}), 400

    row = query('SELECT id, email, password_hash FROM ctgov_user WHERE email=%s', [email], fetchone=True)
    if row and check_password_hash(row['password_hash'], password):
        user = User(row['id'], row['email'], row['password_hash'])
        _complete_login(user)
        return jsonify({'message': 'Logged in successfully.', 'user': _serialize_user(user)}), 200

    return jsonify({'message': 'Invalid credentials.'}), 401


@bp.route('/api/auth/session', methods=['GET'])
@tracer.start_as_current_span("auth.api_session")
def api_session():
    if not current_user.is_authenticated:
        return jsonify({'authenticated': False}), 401
    return jsonify({'authenticated': True, 'user': _serialize_user(current_user)}), 200


@bp.route('/api/auth/logout', methods=['POST'])
@csrf.exempt
@tracer.start_as_current_span("auth.api_logout")
def api_logout():
    if current_user.is_authenticated:
        logout_user()
    return jsonify({'message': 'Logged out.'}), 200
