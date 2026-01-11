from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for, session
from flask_login import login_required, current_user
from extensions import supabase
from utils import load_json_data, get_scenario_by_id
import urllib.parse  # --- FIX 1: Import this to handle URL decoding ---

student_bp = Blueprint('student', __name__)

@student_bp.route("/scenario_select")
@login_required
def scenario_select():
    # Fetch all scenarios using the centralized utility
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
            # Fallback for table naming variations
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
            
            if raw_name and '@' in raw_name:
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

# --- FIX 2: Use <path:> to allow slashes and spaces in ID ---
@student_bp.route("/player/<path:scenario_id>")
@login_required
def player(scenario_id):
    # --- FIX 3: Decode the URL (e.g., "Water%20Leak" -> "Water Leak") ---
    decoded_id = urllib.parse.unquote(scenario_id)
    
    # Debug log for Vercel
    print(f"DEBUG: Player Route. Raw: '{scenario_id}' -> Decoded: '{decoded_id}'")

    # Use the helper function from utils.py with the DECODED ID
    scenario = get_scenario_by_id(decoded_id)

    if not scenario:
        # Debugging: print to Vercel logs to see what's happening
        print(f"ERROR: Scenario ID '{decoded_id}' not found via get_scenario_by_id.")
        flash("Scenario not found or could not be loaded.", "error")
        return redirect(url_for('student.scenario_select'))
    
    print(f"DEBUG: Scenario loaded successfully. Passing to template.")

    # Important: Ensure player.html uses {{ scenario | tojson }}
    return render_template("player.html", scenario=scenario)

@student_bp.route("/quiz/<path:scenario_id>") # Apply similar fix to Quiz route
@login_required
def quiz(scenario_id):
    decoded_id = urllib.parse.unquote(scenario_id)
    scenario = get_scenario_by_id(decoded_id)

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