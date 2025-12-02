from flask import Blueprint, render_template, g
from app.auth import login_required

bp = Blueprint('dashboard', __name__)


@bp.route('/')
def index():
    """Home page / Dashboard"""
    if g.user:
        return render_template('dashboard/index.html')
    return render_template('home/index.html')


@bp.route('/dashboard')
@login_required
def dashboard():
    """User dashboard"""
    return render_template('dashboard/index.html')
