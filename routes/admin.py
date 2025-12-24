from flask import Blueprint, render_template
from flask_login import login_required
from utils import role_required

admin_bp = Blueprint('admin', __name__)

@admin_bp.route("/admin")
@login_required
@role_required('admin')
def dashboard():
    """
    Dedicated Admin Dashboard.
    Requires role='admin' in the Supabase 'profiles' table.
    """
    return render_template("admin.html")