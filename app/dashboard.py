from flask import Blueprint, redirect, render_template, g, url_for
from app.auth import login_required

bp = Blueprint('dashboard', __name__)


@bp.route('/')
def index():
    """Dashboard for logged-in users, login page for everyone else"""
    if g.user:
        return render_template('dashboard/index.html')
    return redirect(url_for('auth.login'))


@bp.route('/dashboard')
@login_required
def dashboard():
    """User dashboard"""
    return render_template('dashboard/index.html')


@bp.route('/newsletter')
@login_required
def newsletter():
    """Newsletter subscription page"""
    return render_template('dashboard/newsletter.html')


@bp.route('/import')
@login_required
def import_page():
    """Import transactions from exchange CSV exports"""
    return render_template('dashboard/import.html')
