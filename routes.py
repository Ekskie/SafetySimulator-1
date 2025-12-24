import os
import json
from flask import render_template, url_for, flash, redirect, request, jsonify, session
from flask_login import login_user, logout_user, login_required, current_user
from app import app, supabase
from models import User
from gotrue.errors import AuthApiError

# Helper to load JSON data
def load_json_data(filename):
    try:
        file_path = os.path.join(app.root_path, filename)
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []

@app.route("/")
def index():
    return render_template("index.html")

# --- Authentication Routes ---

@app.route("/auth")
def auth():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    return render_template("auth.html")

@app.route("/auth/register", methods=['POST'])
def register():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')

    if not email or not password:
        return jsonify({'success': False, 'message': 'Missing email or password'}), 400

    try:
        # Sign up with Supabase
        # The SQL Trigger 'on_auth_user_created' will handle creating the Profile entry
        response = supabase.auth.sign_up({
            "email": email, 
            "password": password
        })

        if response.user:
            return jsonify({
                'success': True, 
                'message': 'Registration successful. Please check your email to verify your account before logging in.'
            })
        else:
            return jsonify({'success': False, 'message': 'Registration failed. Please check your details.'}), 400

    except AuthApiError as e:
        return jsonify({'success': False, 'message': e.message}), 400
    except Exception as e:
        return jsonify({'success': False, 'message': f'System error: {str(e)}'}), 500

@app.route("/auth/login", methods=['POST'])
def login():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')

    try:
        response = supabase.auth.sign_in_with_password({
            "email": email, 
            "password": password
        })

        if response.user:
            user = User(id=response.user.id, email=response.user.email)
            login_user(user)
            
            # Fetch User Role
            role = 'student'
            try:
                profile_res = supabase.table('profiles').select('role').eq('id', response.user.id).single().execute()
                if profile_res.data:
                    role = profile_res.data.get('role', 'student')
            except Exception as e:
                print(f"Error fetching role: {e}")

            # Store credentials in session for persistence across requests
            session['supabase_token'] = response.session.access_token
            session['user_email'] = response.user.email
            session['user_role'] = role
            
            return jsonify({'success': True, 'message': 'Login successful'})

    except AuthApiError as e:
        return jsonify({'success': False, 'message': 'Invalid Login Credentials'}), 401
    except Exception as e:
        return jsonify({'success': False, 'message': f'System error: {str(e)}'}), 500

@app.route("/auth/callback")
def auth_callback():
    return """
    <html>
    <head>
        <title>Verifying Account...</title>
        <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css">
        <style>body { display: flex; align-items: center; justify-content: center; height: 100vh; background: #f8f9fa; }</style>
    </head>
    <body>
    <div class="text-center">
        <div class="spinner-border text-primary mb-3" role="status"></div>
        <h4 class="text-dark">Verifying your account...</h4>
        <p class="text-muted">Please wait while we log you in.</p>
    </div>
    <script>
        const hash = window.location.hash.substring(1);
        const params = new URLSearchParams(hash);
        const accessToken = params.get('access_token');
        const refreshToken = params.get('refresh_token');

        if (accessToken) {
            fetch('/auth/confirm', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ access_token: accessToken, refresh_token: refreshToken })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    window.location.href = '/scenario_select';
                } else {
                    alert('Verification failed: ' + data.message);
                    window.location.href = '/auth';
                }
            })
            .catch(err => {
                console.error('Error:', err);
                window.location.href = '/auth';
            });
        } else {
            window.location.href = '/auth';
        }
    </script>
    </body>
    </html>
    """

@app.route("/auth/confirm", methods=['POST'])
def auth_confirm():
    data = request.get_json()
    access_token = data.get('access_token')
    
    if not access_token:
        return jsonify({'success': False, 'message': 'No access token provided'}), 400

    try:
        user_response = supabase.auth.get_user(access_token)
        if user_response and user_response.user:
            user = User(id=user_response.user.id, email=user_response.user.email)
            login_user(user)
            
            # Fetch User Role
            role = 'student'
            try:
                profile_res = supabase.table('profiles').select('role').eq('id', user_response.user.id).single().execute()
                if profile_res.data:
                    role = profile_res.data.get('role', 'student')
            except Exception as e:
                print(f"Error fetching role: {e}")

            # Store credentials in session
            session['supabase_token'] = access_token
            session['user_email'] = user_response.user.email
            session['user_role'] = role
            
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'message': 'Invalid token'}), 400
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 400

@app.route("/auth/logout")
@login_required
def logout():
    try:
        supabase.auth.sign_out()
    except:
        pass 
    logout_user()
    session.clear()
    return redirect(url_for('index'))

# --- Application Routes ---

@app.route("/scenario_select")
@login_required
def scenario_select():
    scenarios = load_json_data('scenarios.json')
    return render_template("scenario_select.html", scenarios=scenarios)

@app.route("/library")
@login_required
def library():
    scenarios = load_json_data('scenarios.json')
    return render_template("library.html", scenarios=scenarios)

@app.route("/analytics")
@login_required
def analytics():
    return render_template("analytics.html")

# --- UPDATED PROFILE ROUTE ---
@app.route("/profile")
@login_required
def profile():
    try:
        user_id = current_user.id
        user_email = current_user.email
        
        # 1. Fetch Role (Default to 'Student' if not found or error)
        role = 'Student'
        try:
            # Check session first to save a query if available
            if session.get('user_role'):
                role = session.get('user_role').capitalize()
            else:
                profile_res = supabase.table('profiles').select('role').eq('id', user_id).single().execute()
                if profile_res.data:
                    role = profile_res.data.get('role', 'student').capitalize()
        except Exception as e:
            print(f"Error fetching role: {e}")

        # 2. Fetch Progress Stats
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

        # 3. Calculate "Clearance Level" (Gamification)
        # Level 1: 0-2 modules
        # Level 2: 3-5 modules
        # Level 3: 6+ modules
        clearance_level = 1
        level_progress = 0
        
        if completed_count < 3:
            clearance_level = 1
            # Progress to Level 2 (Target: 3)
            level_progress = (completed_count / 3) * 100
        elif completed_count < 6:
            clearance_level = 2
            # Progress to Level 3 (Target: 6)
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
        # Fallback if something critical fails
        return render_template("profile.html", user_email=current_user.email, role="Operator", clearance_level=1, level_progress=0)

# --- NEW: Profile Update Endpoints ---

@app.route("/api/update_email", methods=['POST'])
@login_required
def update_email():
    data = request.get_json()
    new_email = data.get('email')

    if not new_email:
        return jsonify({'success': False, 'message': 'New email is required'}), 400

    try:
        # Update user in Supabase Auth
        # Note: This usually triggers a confirmation email to the new address
        response = supabase.auth.update_user({
            "email": new_email
        })
        
        # If successful, update local session/user details if needed
        # However, typically email updates require re-verification
        
        return jsonify({
            'success': True, 
            'message': 'Confirmation email sent to new address. Please verify to complete the update.'
        })
    except AuthApiError as e:
        return jsonify({'success': False, 'message': e.message}), 400
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route("/api/reset_password", methods=['POST'])
@login_required
def reset_password():
    # Only initiates the flow - usually sends a reset email
    # Or if user is logged in, can update password directly if providing old one?
    # Supabase allows updating password directly if user is authenticated
    data = request.get_json()
    new_password = data.get('password')
    
    if not new_password:
        # If no password provided, assume request for reset email flow
        email = current_user.email
        try:
            supabase.auth.reset_password_email(email)
            return jsonify({'success': True, 'message': 'Password reset link sent to your email.'})
        except Exception as e:
            return jsonify({'success': False, 'message': str(e)}), 400
            
    # If password provided (User changing password directly)
    try:
        response = supabase.auth.update_user({
            "password": new_password
        })
        return jsonify({'success': True, 'message': 'Password updated successfully.'})
    except Exception as e:
         return jsonify({'success': False, 'message': str(e)}), 400

@app.route("/tutorial")
def tutorial():
    return render_template("tutorial.html")

@app.route("/about")
def about():
    return render_template("about.html")

# --- FACULTY DASHBOARD (Protected) ---
@app.route("/faculty")
@login_required
def faculty():
    try:
        user_id = current_user.id
        
        # 1. Verify Faculty Role
        profile_res = supabase.table('profiles').select('role').eq('id', user_id).single().execute()
        
        if not profile_res.data or profile_res.data.get('role') != 'faculty':
            flash("Access Denied: You must be a Faculty member to view this page.", "error")
            return redirect(url_for('scenario_select'))

        # 2. Fetch Data
        # We need profiles to get emails/names
        profiles_response = supabase.table('profiles').select('id, email').execute()
        profiles_map = {p['id']: p['email'] for p in profiles_response.data}

        response = supabase.table('user_progress').select('*').execute()
        progress_data = response.data
        
        # Aggregate by User
        students_map = {}
        total_completions = 0
        total_score_sum = 0
        total_records = 0

        for record in progress_data:
            uid = record['user_id']
            if uid not in students_map:
                # Use email as name if available, otherwise masked ID
                email = profiles_map.get(uid, "Unknown")
                name_display = email.split('@')[0].title() if '@' in email else uid[:8] + '...'
                
                students_map[uid] = {
                    'id': uid, # Keep full ID for data-attributes
                    'name': name_display, # NEW: Display Name
                    'email': email,       # NEW: Email for details
                    'active_count': 0,
                    'completed_count': 0,
                    'total_score': 0,
                    'last_active': record.get('created_at', '')[:10],
                    'scenarios': [] # NEW: List of taken scenarios for the modal
                }
            
            # Add specific scenario detail
            students_map[uid]['scenarios'].append({
                'title': record.get('scenario_id', 'Unknown Module'), # ideally fetch title from JSON
                'score': record['score'],
                'completed': record['completed'],
                'date': record.get('completed_at', record.get('created_at', ''))[:10]
            })

            students_map[uid]['active_count'] += 1
            students_map[uid]['total_score'] += record['score']
            
            if record['completed']:
                students_map[uid]['completed_count'] += 1
                total_completions += 1
            
            total_score_sum += record['score']
            total_records += 1

        # Calculate averages
        students_list = []
        for uid, s in students_map.items():
            s['avg_score'] = round(s['total_score'] / s['active_count']) if s['active_count'] > 0 else 0
            students_list.append(s)
        
        avg_class_score = round(total_score_sum / total_records) if total_records > 0 else 0

        return render_template("faculty.html", 
                               students=students_list, 
                               total_completions=total_completions, 
                               avg_score=avg_class_score)
    except Exception as e:
        print(f"Error fetching faculty data: {e}")
        flash("System Error: Could not retrieve faculty data.", "error")
        return redirect(url_for('index'))

@app.route("/player/<scenario_id>")
@login_required
def player(scenario_id):
    all_scenarios = load_json_data('scenarios.json')
    scenario = next((s for s in all_scenarios if str(s['id']) == str(scenario_id)), None)

    # Use PC1scenario for specific ID or fallback
    if scenario_id == "PC1" or scenario_id == "lab_chemical_spill":
        detailed_data = load_json_data('PC1scenario.json')
        if detailed_data:
            if isinstance(detailed_data, list):
                # Try to find match in list
                detailed_match = next((s for s in detailed_data if str(s['id']) == str(scenario_id)), None)
                if detailed_match:
                    scenario = detailed_match
                elif len(detailed_data) > 0:
                     # Fallback to first item if strict ID match fails but file exists
                    scenario = detailed_data[0]
            else:
                scenario = detailed_data

    if not scenario:
        flash("Scenario not found.", "error")
        return redirect(url_for('scenario_select'))

    return render_template("player.html", scenario=scenario)

@app.route("/quiz/<scenario_id>")
@login_required
def quiz(scenario_id):
    all_scenarios = load_json_data('scenarios.json')
    scenario = next((s for s in all_scenarios if str(s['id']) == str(scenario_id)), None)

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
        return redirect(url_for('scenario_select'))
        
    return render_template("quiz.html", scenario=scenario)

# --- API Endpoints ---

@app.route("/api/save_progress", methods=['POST'])
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
        print(f"Error saving progress: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route("/api/get_analytics")
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