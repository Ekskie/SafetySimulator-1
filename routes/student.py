from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for, session, Response, stream_with_context
from flask_login import login_required, current_user
import requests
from extensions import supabase
from utils import load_json_data

student_bp = Blueprint('student', __name__)

@student_bp.route("/scenario_select")
@login_required
def scenario_select():
    # This now fetches from Supabase via utils.py
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

@student_bp.route("/leaderboard")
@login_required
def leaderboard():
    try:
        # 1. Fetch Profiles
        try:
            profiles_res = supabase.table('profiles').select('*').execute()
        except:
            profiles_res = supabase.table('profile').select('*').execute()
            
        profiles = profiles_res.data if profiles_res.data else []
        
        # 2. Fetch Progress
        progress_res = supabase.table('user_progress').select('*').eq('completed', True).execute()
        progress_data = progress_res.data if progress_res.data else []
        
        # 3. Calculate Scores
        user_scores = {}
        for item in progress_data:
            uid = str(item.get('user_id'))
            score = item.get('score', 0)
            user_scores[uid] = user_scores.get(uid, 0) + score
                
        # 4. Build Data
        leaderboard_data = []
        current_user_id_str = str(current_user.id)

        for p in profiles:
            uid = str(p.get('id'))
            
            # Name Logic
            if uid == current_user_id_str:
                raw_name = p.get('full_name') or current_user.email
            else:
                raw_name = p.get('full_name') or p.get('email') or "Unknown Cadet"
            
            if '@' in raw_name:
                name = raw_name.split('@')[0]
            else:
                name = raw_name
            
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
            
        # 5. Sort
        leaderboard_data.sort(key=lambda x: x['points'], reverse=True)
        top_users = leaderboard_data[:50]
        
        # 6. Get Current User Stats
        current_user_stats = next((u for u in leaderboard_data if u['id'] == current_user_id_str), None)
        
        if not current_user_stats:
            current_email = getattr(current_user, 'email', '')
            current_name = current_email.split('@')[0] if '@' in current_email else "You"
            
            current_user_stats = {
                'id': current_user_id_str,
                'name': current_name,
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

@student_bp.route("/player/<scenario_id>")
@login_required
def player(scenario_id):
    # Load all scenarios from DB (via utils.py)
    all_scenarios = load_json_data('scenarios.json')
    
    # Find the matching scenario
    # We cast IDs to strings to ensure matching works ('1' vs 1)
    scenario = next((s for s in all_scenarios if str(s['id']) == str(scenario_id)), None)

    # REMOVED: Legacy fallback to PC1scenario.json. 
    # The DB is now the single source of truth.

    if not scenario:
        flash("Scenario not found.", "error")
        return redirect(url_for('student.scenario_select'))

    return render_template("player.html", scenario=scenario)

@student_bp.route("/quiz/<scenario_id>")
@login_required
def quiz(scenario_id):
    all_scenarios = load_json_data('scenarios.json')
    scenario = next((s for s in all_scenarios if str(s['id']) == str(scenario_id)), None)

    # REMOVED: Legacy fallback to PC1scenario.json.

    if not scenario:
        return redirect(url_for('student.scenario_select'))
        
    return render_template("quiz.html", scenario=scenario)

# --- Proxy Route for GDrive ---
@student_bp.route("/proxy/<file_id>")
@login_required
def proxy_stream(file_id):
    """
    Proxies the Google Drive stream to the client.
    Handles the 'Virus Scan' confirmation for large files.
    """
    def get_confirm_token(response):
        for key, value in response.cookies.items():
            if key.startswith('download_warning'):
                return value
        return None

    def save_response_content(response):
        # Generator to stream content chunk by chunk
        # This prevents loading the entire video into RAM
        for chunk in response.iter_content(chunk_size=32 * 1024):
            if chunk:
                yield chunk

    URL = "https://docs.google.com/uc?export=download"
    session_req = requests.Session()

    # 1. Initial request
    response = session_req.get(URL, params={'id': file_id}, stream=True)

    # 2. Check for "Virus Scan" warning token
    token = get_confirm_token(response)

    if token:
        # 3. If warning exists, re-request with confirmation token
        params = {'id': file_id, 'confirm': token}
        response = session_req.get(URL, params=params, stream=True)

    # 4. Stream the response back to the browser
    # We copy the content type so the browser knows it's a video
    return Response(
        stream_with_context(save_response_content(response)),
        content_type=response.headers.get('Content-Type', 'video/mp4'),
        direct_passthrough=True
    )

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