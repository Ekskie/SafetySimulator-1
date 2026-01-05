import os
import json
from flask import current_app, flash, redirect, url_for
from flask_login import current_user
from functools import wraps
from extensions import supabase

def get_base_path():
    """
    Helper to get the base path safely, working on both Vercel and Local.
    """
    try:
        return current_app.root_path
    except RuntimeError:
        # Fallback if accessed outside of application context
        return os.path.dirname(os.path.abspath(__file__))

def load_json_data(filename):
    """
    Helper to load data. 
    If filename is 'scenarios.json', it fetches live data from Supabase.
    Otherwise, it falls back to loading from the local file system.
    """
    if filename == 'scenarios.json':
        try:
            # Fetch all rows from the 'scenarios' table
            response = supabase.table('scenarios').select('*').execute()
            data = response.data
            
            # Map Database columns (snake_case) to Application keys (camelCase)
            formatted_data = []
            for row in data:
                scenario = {
                    "id": row.get('id'),
                    "title": row.get('title'),
                    "description": row.get('description'),
                    "workplace": row.get('workplace'),
                    "subcategory": row.get('subcategory'),
                    "hazards": row.get('hazards'),
                    "difficulty": row.get('difficulty'),
                    "duration": row.get('duration'),
                    "completions": row.get('completions'),
                    "avgScore": row.get('avg_score'),   
                    "startNode": row.get('start_node'), 
                    "nodes": row.get('nodes'),          
                    "quiz": row.get('quiz'),
                    # Keep content_file for backward compatibility if needed
                    "content_file": row.get('content_file')
                }
                formatted_data.append(scenario)
            
            return formatted_data

        except Exception as e:
            print(f"Error fetching scenarios from Supabase: {e}")
            return []

    # Default behavior for other files (fallback to disk)
    try:
        file_path = os.path.join(get_base_path(), filename)
        if not os.path.exists(file_path):
            return None
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []

def get_scenario_by_id(scenario_id):
    """
    Helper to find a specific scenario from the list.
    Now fetches from Supabase via load_json_data.
    """
    scenarios = load_json_data('scenarios.json')
    str_id = str(scenario_id)
    
    for scenario in scenarios:
        if str(scenario.get('id')) == str_id:
            return scenario
            
    return None

def load_scenario_content(content_identifier):
    """
    Helper to load specific scenario content.
    If the data is already in Supabase (inside the 'nodes' column), 
    we don't need to load an external file.
    """
    # If the identifier looks like a filename, try to load it
    if str(content_identifier).endswith('.json'):
        return load_json_data(content_identifier)
    
    # Otherwise, it might be the content object itself or we might need to fetch it
    return None

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