from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for, session
from flask_login import login_required, current_user
from extensions import supabase
import json
from datetime import datetime
import os

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

def format_time_ago(timestamp_str):
    """Helper to convert ISO timestamp to '2 hours ago' format"""
    try:
        if not timestamp_str: return ""
        dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        now = datetime.now(dt.tzinfo)
        diff = now - dt
        seconds = diff.total_seconds()
        if seconds < 60: return "Just now"
        elif seconds < 3600: return f"{int(seconds // 60)} mins ago"
        elif seconds < 86400: return f"{int(seconds // 3600)} hours ago"
        else: return f"{int(seconds // 86400)} days ago"
    except Exception as e:
        return timestamp_str.split('T')[0]

@admin_bp.route("/")
@admin_bp.route("/dashboard")
@login_required
def dashboard():
    # ... (Dashboard logic remains unchanged) ...
    stats = {
        'total_students': 0,
        'active_scenarios': 0,
        'pending_approvals': 0,
        'avg_score': 0
    }
    recent_activity = []

    try:
        students_res = supabase.table('profiles').select('*', count='exact').eq('role', 'student').execute()
        stats['total_students'] = students_res.count if students_res.count is not None else len(students_res.data)

        scenarios_res = supabase.table('scenarios').select('*', count='exact').execute()
        stats['active_scenarios'] = scenarios_res.count if scenarios_res.count is not None else len(scenarios_res.data)

        progress_res = supabase.table('user_progress').select('score').execute()
        if progress_res.data:
            scores = [p['score'] for p in progress_res.data if p['score'] is not None]
            if scores:
                stats['avg_score'] = round(sum(scores) / len(scores))

        pending_res = supabase.table('profiles').select('*', count='exact').eq('role', 'pending').execute()
        stats['pending_approvals'] = pending_res.count if pending_res.count is not None else 0

        logs_res = supabase.table('quiz_logs').select('*').order('created_at', desc=True).limit(5).execute()
        
        if logs_res.data:
            for log in logs_res.data:
                user_id = log.get('user_id')
                scenario_title = log.get('scenario_title', 'Unknown Scenario')
                score = log.get('score', 0)
                
                if score >= 80:
                    icon = "fas fa-check-circle"
                    color = "#2ecc71"
                    bg_color = "#e8f8f5"
                    msg = f"completed <strong>{scenario_title}</strong> with High Distinction"
                elif score >= 50:
                    icon = "fas fa-check"
                    color = "#3498db"
                    bg_color = "#ebf8ff"
                    msg = f"completed <strong>{scenario_title}</strong>"
                else:
                    icon = "fas fa-exclamation-circle"
                    color = "#e74c3c"
                    bg_color = "#fef2f2"
                    msg = f"failed <strong>{scenario_title}</strong>"

                recent_activity.append({
                    'icon': icon,
                    'color': color,
                    'bg_color': bg_color,
                    'message': msg,
                    'time_ago': format_time_ago(log.get('created_at'))
                })

    except Exception as e:
        print(f"Error loading admin dashboard: {e}")

    return render_template("admin/admin.html", stats=stats, activity=recent_activity)

@admin_bp.route("/scenario_builder")
@login_required
def scenario_builder():
    return render_template("admin/scenario_builder.html", 
                         supabase_url=os.environ.get("SUPABASE_URL"),
                         supabase_key=os.environ.get("SUPABASE_KEY"))

@admin_bp.route("/save_scenario", methods=['POST'])
@login_required
def save_scenario():
    try:
        data = request.get_json()
        filename = data.get('filename') # Acts as the ID
        content = data.get('content') # The full data object from frontend

        if not filename or not content:
            return jsonify({'success': False, 'message': 'Missing data'})

        # 1. Clean up ID
        clean_id = filename.replace('.json', '') # e.g. "agri culture"
        
        # 2. Extract Fields
        # IMPORTANT: 'nodes' and 'quiz' should be passed as Python objects (lists/dicts),
        # NOT json.dumps strings. Supabase client handles the JSON conversion.
        
        nodes_data = content.get('nodes', [])
        quiz_data = content.get('quiz', {})
        
        # Handle metadata fields
        title = content.get('title', clean_id.title())
        description = content.get('description', 'No description provided.')
        difficulty = content.get('difficulty', 'Medium')
        duration = content.get('duration', 10)
        
        # New fields required by your schema
        workplace = content.get('workplace', 'laboratory') # Default
        subcategory = content.get('subcategory', 'general') # Default
        
        # Ensure hazards is a list
        hazards = content.get('hazards', [])
        if isinstance(hazards, str):
            hazards = [h.strip() for h in hazards.split(',')]
            
        # Construct the record
        record = {
            'id': clean_id,
            'title': title,
            'description': description,
            'start_node': content.get('start_node', ''),
            
            # --- FIX: Store as raw objects, NOT strings ---
            'nodes': nodes_data, 
            'quiz': quiz_data,   
            
            'workplace': workplace,
            'subcategory': subcategory,
            'difficulty': difficulty,
            'duration': duration,
            'hazards': hazards,
            'created_at': 'now()'
        }

        print(f"Saving Scenario: {clean_id}")
        
        # 3. Upsert to Supabase
        res = supabase.table('scenarios').upsert(record).execute()

        return jsonify({'success': True, 'message': f'Scenario "{clean_id}" saved successfully!'})

    except Exception as e:
        print(f"Save Error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': str(e)}), 500