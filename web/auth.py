from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import LoginManager, login_user, logout_user, login_required, UserMixin
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import datetime, timedelta
import secrets
from .db import query, execute

bp = Blueprint('auth', __name__)
login_manager = LoginManager()
login_manager.login_view = 'auth.login'


class User(UserMixin):
    def __init__(self, id_, email, password_hash, is_organization):
        self.id = id_
        self.email = email
        self.password_hash = password_hash
        self.is_organization = is_organization

    @staticmethod
    def get(user_id):
        row = query('SELECT id, email, password_hash, is_organization FROM ctgov_user WHERE id=%s', [user_id], fetchone=True)
        if row:
            return User(row['id'], row['email'], row['password_hash'], row['is_organization'])
        return None

@login_manager.user_loader
def load_user(user_id):
    return User.get(user_id)


@bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        row = query('SELECT id, email, password_hash, is_organization FROM ctgov_user WHERE email=%s', [email], fetchone=True)
        if row and check_password_hash(row['password_hash'], password):
            user = User(row['id'], row['email'], row['password_hash'], row['is_organization'])
            login_user(user)
            execute('INSERT INTO login_activity (user_id) VALUES (%s)', [user.id])
            flash('Logged in successfully.', 'success')
            return redirect(url_for('dashboard.index'))
        flash('Invalid credentials', 'danger')
    return render_template('login.html')


@bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        existing = query('SELECT id FROM ctgov_user WHERE email=%s', [email], fetchone=True)
        email_domain = email.partition("@")[2]
        org_check = query('SELECT id FROM organization WHERE email_domain=%s', [email_domain], fetchone=True)
        if existing:
            flash('Email already registered', 'danger')
        else:
            password_hash = generate_password_hash(password)
            if org_check:
                execute('INSERT INTO ctgov_user (email, password_hash, is_organization) VALUES (%s, %s, %s)', [email, password_hash, True])
            else:
                execute('INSERT INTO ctgov_user (email, password_hash) VALUES (%s, %s)', [email, password_hash])
            flash('Registration successful. Please log in.', 'success')
            return redirect(url_for('auth.login'))
    return render_template('register.html')


@bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))


@bp.route('/reset', methods=['GET', 'POST'])
def reset_request():
    if request.method == 'POST':
        email = request.form['email']
        user = query('SELECT id FROM ctgov_user WHERE email=%s', [email], fetchone=True)
        if user:
            token = secrets.token_urlsafe(32)
            expires_at = datetime.now(datetime.timezone.utc) + timedelta(hours=1)
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
    return render_template('reset_request.html')


@bp.route('/reset/<token>', methods=['GET', 'POST'])
def reset_password(token):
    row = query('SELECT id, user_id, expires_at FROM password_reset WHERE token=%s', [token], fetchone=True)
    if not row or row['expires_at'] < datetime.now(datetime.timezone.utc):
        flash('Invalid or expired token.', 'danger')
        return redirect(url_for('auth.reset_request'))
    if request.method == 'POST':
        password = request.form['password']
        password_hash = generate_password_hash(password)
        execute('UPDATE ctgov_user SET password_hash=%s WHERE id=%s', [password_hash, row['user_id']])
        execute('DELETE FROM password_reset WHERE id=%s', [row['id']])
        flash('Password updated. Please log in.', 'success')
        return redirect(url_for('auth.login'))
    return render_template('reset_password.html')
