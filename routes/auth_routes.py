
from flask import (
    Blueprint, render_template, request, redirect,
    url_for, flash, session
)
from werkzeug.security import check_password_hash

from database.db import execute_query

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if session.get('user_id'):
        return redirect(url_for('main.dashboard'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        if not username or not password:
            flash('Please enter both username and password.', 'warning')
            return render_template('login.html')

        try:
            user = execute_query(
                """
                SELECT user_id, staff_id, username, password_hash, role
                FROM users
                WHERE username = %s AND is_active = 1
                """,
                (username,),
                fetch='one'
            )

            if user and check_password_hash(
                user['password_hash'], password
            ):
                session.clear()
                session['user_id'] = user['user_id']
                session['username'] = user['username']
                session['role'] = user['role']
                session['staff_id'] = user['staff_id']

                flash('Login successful.', 'success')
                return redirect(url_for('main.dashboard'))

            flash('Invalid username or password.', 'danger')

        except Exception:
            flash('Unable to log in. Please try again.', 'danger')

    return render_template('login.html')


@auth_bp.route('/logout', methods=['POST'])
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))
