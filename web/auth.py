from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import LoginManager, login_user, logout_user, login_required, UserMixin
from werkzeug.security import check_password_hash
from .db import query, execute

bp = Blueprint('auth', __name__)
login_manager = LoginManager()
login_manager.login_view = 'auth.login'


class User(UserMixin):
    def __init__(self, id_, email, password_hash):
        self.id = id_
        self.email = email
        self.password_hash = password_hash

    @staticmethod
    def get(user_id):
        row = query('SELECT id, email, password_hash FROM ctgov_user WHERE id=%s', [user_id], fetchone=True)
        if row:
            return User(row['id'], row['email'], row['password_hash'])
        return None

@login_manager.user_loader
def load_user(user_id):
    return User.get(user_id)


@bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        row = query('SELECT id, email, password_hash FROM ctgov_user WHERE email=%s', [email], fetchone=True)
        if row and check_password_hash(row['password_hash'], password):
            user = User(row['id'], row['email'], row['password_hash'])
            login_user(user)
            execute('INSERT INTO login_activity (user_id) VALUES (%s)', [user.id])
            flash('Logged in successfully.', 'success')
            return redirect(url_for('dashboard.index'))
        flash('Invalid credentials', 'danger')
    return render_template('login.html')


@bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))
