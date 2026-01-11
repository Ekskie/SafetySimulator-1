from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for, session
from flask_login import login_required, current_user
from extensions import supabase
from utils import load_json_data, get_scenario_by_id
import urllib.parse
from datetime import datetime

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

# --- CERTIFICATE ROUTES ---

@student_bp.route("/certificates")
@login_required
def certificates():
    try:
        user_id = current_user.id
        scenarios_res = supabase.table('scenarios').select('*', count='exact').execute()
        total_count = scenarios_res.count if scenarios_res.count is not None else 0

        logs_res = supabase.table('quiz_logs').select('scenario_title').eq('user_id', user_id).gte('score', 50).execute()
        
        completed_scenarios = set()
        if logs_res.data:
            for log in logs_res.data:
                completed_scenarios.add(log.get('scenario_title'))
        
        completed_count = len(completed_scenarios)
        
        progress_percent = 0
        if total_count > 0:
            progress_percent = int((completed_count / total_count) * 100)
            
        if progress_percent > 100: progress_percent = 100
            
        is_eligible = (completed_count >= total_count) and (total_count > 0)

        return render_template('certificates.html', 
                             total_count=total_count,
                             completed_count=completed_count,
                             progress_percent=progress_percent,
                             is_eligible=is_eligible)

    except Exception as e:
        print(f"Certificate Error: {e}")
        return render_template('certificates.html', 
                             total_count=0,
                             completed_count=0,
                             progress_percent=0,
                             is_eligible=False)

@student_bp.route("/certificate/view")
@login_required
def view_certificate():
    student_name = getattr(current_user, 'username', 'Student Name')
    if not student_name or student_name == 'Unknown':
        student_name = current_user.email.split('@')[0] if current_user.email else "Student Name"

    date_str = datetime.now().strftime("%B %d, %Y")
    
    return render_template('view_certificate.html', 
                         student_name=student_name,
                         date=date_str)

# --- LEADERBOARD & PROFILE ---

@student_bp.route("/leaderboard")
@login_required
def leaderboard():
    try:
        try:
            profiles_res = supabase.table('profiles').select('*').execute()
        except:
            profiles_res = supabase.table('profile').select('*').execute()
            
        profiles = profiles_res.data if profiles_res.data else []
        progress_res = supabase.table('user_progress').select('*').eq('completed', True).execute()
        progress_data = progress_res.data if progress_res.data else []
        
        user_scores = {}
        for item in progress_data:
            uid = str(item.get('user_id'))
            score = item.get('score', 0)
            user_scores[uid] = user_scores.get(uid, 0) + score
                
        leaderboard_data = []
        current_user_id_str = str(current_user.id)

        for p in profiles:
            uid = str(p.get('id'))
            if uid == current_user_id_str:
                name = current_user.username
            else:
                raw_name = p.get('full_name') or p.get('email') or "Unknown Cadet"
                name = raw_name.split('@')[0] if raw_name and '@' in raw_name else raw_name
            
            role = p.get('role', 'student').lower()
            total_points = user_scores.get(uid, 0)
            
            badges = []
            if total_points >= 1000: badges.append("Safety Champion")
            if total_points >= 500: badges.append("Expert")
            elif total_points >= 100: badges.append("Novice")
                
            leaderboard_data.append({
                'id': uid,
                'name': name,
                'role': role,
                'points': total_points,
                'badges': badges
            })
            
        leaderboard_data.sort(key=lambda x: x['points'], reverse=True)
        top_users = leaderboard_data[:50]
        
        current_user_stats = next((u for u in leaderboard_data if u['id'] == current_user_id_str), None)
        if not current_user_stats:
            current_user_stats = {
                'id': current_user_id_str,
                'name': current_user.username,
                'role': session.get('user_role', 'student'),
                'points': 0,
                'badges': []
            }

        return render_template('leaderboard.html', top_users=top_users, user_stats=current_user_stats)

    except Exception as e:
        print(f"Leaderboard error: {e}")
        flash("Unable to load leaderboard stats.", "error")
        return redirect(url_for('general.index'))
    
@student_bp.route("/profile")
@login_required
def profile():
    try:
        user_id = current_user.id
        user_email = current_user.email
        role = session.get('user_role', 'student').capitalize()

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

# --- TRAINING ROUTES ---

@student_bp.route("/player/<path:scenario_id>")
@login_required
def player(scenario_id):
    decoded_id = urllib.parse.unquote(scenario_id)
    scenario = get_scenario_by_id(decoded_id)
    if not scenario:
        flash("Scenario not found.", "error")
        return redirect(url_for('student.scenario_select'))
    return render_template("player.html", scenario=scenario)

@student_bp.route("/quiz/<path:scenario_id>")
@login_required
def quiz(scenario_id):
    decoded_id = urllib.parse.unquote(scenario_id)
    scenario = get_scenario_by_id(decoded_id)
    if not scenario:
        return redirect(url_for('student.scenario_select'))
    return render_template("quiz.html", scenario=scenario)

# --- STUDENT API ENDPOINTS (Correctly placed here for /api/ prefix) ---

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

@student_bp.route("/api/update_profile", methods=['POST'])
@login_required
def update_profile():
    data = request.get_json()
    new_name = data.get('full_name')
    
    if not new_name:
        return jsonify({'success': False, 'message': 'Name cannot be empty'}), 400
        
    try:
        # Update the profiles table
        supabase.table('profiles').update({'full_name': new_name}).eq('id', current_user.id).execute()
        
        # Update session if used
        if 'user' in session:
            session['user']['name'] = new_name
            session.modified = True
            
        return jsonify({'success': True, 'message': 'Profile updated successfully'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@student_bp.route("/api/update_email", methods=['POST'])
@login_required
def update_email():
    data = request.get_json()
    new_email = data.get('email')
    if not new_email:
        return jsonify({'success': False, 'message': 'New email required'}), 400
    try:
        supabase.auth.update_user({"email": new_email})
        return jsonify({'success': True, 'message': 'Confirmation email sent.'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@student_bp.route("/api/reset_password", methods=['POST'])
@login_required
def reset_password():
    data = request.get_json()
    new_password = data.get('password')
    
    try:
        if not new_password:
            # Send reset link to current email
            supabase.auth.reset_password_email(current_user.email)
            return jsonify({'success': True, 'message': 'Reset link sent.'})
        
        # Update directly (if logged in)
        supabase.auth.update_user({"password": new_password})
        return jsonify({'success': True, 'message': 'Password updated.'})
    except Exception as e:
         return jsonify({'success': False, 'message': str(e)}), 400