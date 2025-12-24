from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for, session
from flask_login import login_required, current_user
from extensions import supabase
from utils import load_json_data

student_bp = Blueprint('student', __name__)

@student_bp.route("/scenario_select")
@login_required
def scenario_select():
    scenarios = load_json_data('scenarios.json')
    return render_template("scenario_select.html", scenarios=scenarios)

@student_bp.route("/library")
@login_required
def library():
    scenarios = load_json_data('scenarios.json')
    return render_template("library.html", scenarios=scenarios)

@student_bp.route("/analytics")
@login_required
def analytics():
    return render_template("analytics.html")

@student_bp.route("/profile")
@login_required
def profile():
    try:
        user_id = current_user.id
        user_email = current_user.email
        
        # Determine Role
        role = session.get('user_role', 'student').capitalize()

        # Fetch Progress
        completed_count = 0
        total_xp = 0 
        
        try:
            progress_res = supabase.table('user_progress').select('*').eq('user_id', user_id).eq('completed', True).execute()
            data = progress_res.data
            if data:
                completed_count = len(data)
                total_xp = sum(item['score'] for item in data)
        except Exception as e:
            print(f"Error fetching progress: {e}")

        # Gamification Level Logic
        clearance_level = 1
        level_progress = 0
        
        if completed_count < 3:
            clearance_level = 1
            level_progress = (completed_count / 3) * 100
        elif completed_count < 6:
            clearance_level = 2
            level_progress = ((completed_count - 3) / 3) * 100
        else:
            clearance_level = 3
            level_progress = 100

        return render_template("profile.html", 
                               user_email=user_email,
                               role=role,
                               clearance_level=clearance_level,
                               level_progress=round(level_progress),
                               completed_count=completed_count,
                               total_xp=total_xp)
    except Exception as e:
        print(f"Profile Error: {e}")
        return render_template("profile.html", user_email=current_user.email, role="Operator", clearance_level=1, level_progress=0)

@student_bp.route("/player/<scenario_id>")
@login_required
def player(scenario_id):
    all_scenarios = load_json_data('scenarios.json')
    scenario = next((s for s in all_scenarios if str(s['id']) == str(scenario_id)), None)

    # Detailed data fallback for specific ID
    if scenario_id == "PC1" or scenario_id == "lab_chemical_spill":
        detailed_data = load_json_data('PC1scenario.json')
        if detailed_data:
            if isinstance(detailed_data, list):
                detailed_match = next((s for s in detailed_data if str(s['id']) == str(scenario_id)), None)
                if detailed_match:
                    scenario = detailed_match
                elif len(detailed_data) > 0:
                    scenario = detailed_data[0]
            else:
                scenario = detailed_data

    if not scenario:
        flash("Scenario not found.", "error")
        return redirect(url_for('student.scenario_select'))

    return render_template("player.html", scenario=scenario)

@student_bp.route("/quiz/<scenario_id>")
@login_required
def quiz(scenario_id):
    all_scenarios = load_json_data('scenarios.json')
    scenario = next((s for s in all_scenarios if str(s['id']) == str(scenario_id)), None)

    # Logic to load detailed quiz data if needed
    if scenario_id == "PC1" or scenario_id == "lab_chemical_spill":
        detailed_data = load_json_data('PC1scenario.json')
        if detailed_data:
             if isinstance(detailed_data, list):
                detailed_match = next((s for s in detailed_data if str(s['id']) == str(scenario_id)), None)
                if detailed_match:
                    scenario = detailed_match
                elif len(detailed_data) > 0:
                    scenario = detailed_data[0]
             else:
                scenario = detailed_data

    if not scenario:
        return redirect(url_for('student.scenario_select'))
        
    return render_template("quiz.html", scenario=scenario)

# --- Student APIs ---

@student_bp.route("/api/save_progress", methods=['POST'])
@login_required
def save_progress():
    data = request.get_json()
    scenario_id = data.get('scenario_id')
    score = data.get('score')
    scenario_title = data.get('scenario_title')
    user_id = current_user.id

    try:
        supabase.table('quiz_logs').insert({
            'user_id': user_id,
            'scenario_id': scenario_id,
            'scenario_title': scenario_title,
            'score': score
        }).execute()

        existing = supabase.table('user_progress').select('*').eq('user_id', user_id).eq('scenario_id', scenario_id).execute()
        
        should_update = True
        if existing.data:
            current_record = existing.data[0]
            if current_record['completed'] and score <= current_record['score']:
                should_update = False
        
        if should_update:
            if existing.data:
                supabase.table('user_progress').update({
                    'score': score,
                    'completed': True,
                    'completed_at': 'now()'
                }).eq('id', existing.data[0]['id']).execute()
            else:
                supabase.table('user_progress').insert({
                    'user_id': user_id,
                    'scenario_id': scenario_id,
                    'score': score,
                    'completed': True
                }).execute()
                
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@student_bp.route("/api/get_analytics")
@login_required
def get_analytics():
    user_id = current_user.id
    try:
        progress_response = supabase.table('user_progress').select('*').eq('user_id', user_id).execute()
        logs_response = supabase.table('quiz_logs').select('*').eq('user_id', user_id).order('attempted_at', desc=True).execute()
        
        return jsonify({
            'progress': progress_response.data,
            'logs': logs_response.data
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500