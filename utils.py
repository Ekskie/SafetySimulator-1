import os
import json
from flask import current_app, flash, redirect, url_for
from flask_login import current_user
from functools import wraps
from extensions import supabase

def load_json_data(filename):
    """Helper to load JSON data from the root path."""
    try:
        file_path = os.path.join(current_app.root_path, filename)
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []

def role_required(required_role):
    """
    Decorator to restrict access to a specific role (student, faculty, admin).
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for('auth.auth'))
            
            user_id = current_user.id
            try:
                # Check profile for role
                profile_res = supabase.table('profiles').select('role').eq('id', user_id).single().execute()
                
                # Default to student if no role found
                user_role = profile_res.data.get('role', 'student') if profile_res.data else 'student'
                
                if user_role != required_role:
                    flash(f"Access Denied: You must be a {required_role.capitalize()} to view this page.", "error")
                    return redirect(url_for('general.index'))
                    
            except Exception as e:
                print(f"Role Check Error: {e}")
                flash("System Error: Could not verify access level.", "error")
                return redirect(url_for('general.index'))
                
            return f(*args, **kwargs)
        return decorated_function
    return decorator