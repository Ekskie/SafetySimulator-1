from flask import Blueprint, render_template, session, redirect, url_for, flash, request, jsonify
from flask_login import login_required
from utils import role_required
import json
import os

admin_bp = Blueprint('admin', __name__,
                     template_folder='../templates/admin',)

@admin_bp.route('/admin')
@login_required
@role_required('admin')
def dashboard():
    return render_template('admin.html')

@admin_bp.route('/admin/scenario-builder')
@login_required
@role_required('admin')
def scenario_builder():
    return render_template('scenario_builder.html')

@admin_bp.route('/admin/save-scenario', methods=['POST'])
@login_required
@role_required('admin')
def save_scenario():
    try:
        data = request.get_json()
        filename = data.get('filename', 'new_scenario.json')
        scenario_content = data.get('content')

        if not filename.endswith('.json'):
            filename += '.json'

        # Basic security: ensure we only write to the scenarios directory or root
        # taking the basename strips any directory traversal attempts (e.g. ../../)
        safe_filename = os.path.basename(filename)
        
        # Save the file
        with open(safe_filename, 'w') as f:
            json.dump(scenario_content, f, indent=4)
            
        return jsonify({"success": True, "message": f"Saved {safe_filename} successfully!"})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500
