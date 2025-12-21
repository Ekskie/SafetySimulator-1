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
            
            # Store credentials in session for persistence across requests
            session['supabase_token'] = response.session.access_token
            session['user_email'] = response.user.email  # <--- CRITICAL FIX
            
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
            
            # Store credentials in session
            session['supabase_token'] = access_token
            session['user_email'] = user_response.user.email # <--- CRITICAL FIX
            
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
    session.clear() # This clears user_email too
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

@app.route("/profile")
@login_required
def profile():
    # Use current_user.email directly now that app.py loads it correctly
    user_email = current_user.email
    return render_template("profile.html", user_email=user_email)

@app.route("/tutorial")
def tutorial():
    return render_template("tutorial.html")

@app.route("/about")
def about():
    return render_template("about.html")

@app.route("/player/<scenario_id>")
@login_required
def player(scenario_id):
    all_scenarios = load_json_data('scenarios.json')
    scenario = next((s for s in all_scenarios if str(s['id']) == str(scenario_id)), None)

    if scenario_id == "PC1" or (scenario and scenario.get('detail_file')):
        detailed_data = load_json_data('PC1scenario.json')
        if detailed_data:
            if isinstance(detailed_data, list):
                detailed_match = next((s for s in detailed_data if str(s['id']) == str(scenario_id)), None)
                if detailed_match:
                    scenario = detailed_match
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

    if scenario_id == "PC1":
        detailed_data = load_json_data('PC1scenario.json')
        if detailed_data:
             if isinstance(detailed_data, list):
                detailed_match = next((s for s in detailed_data if str(s['id']) == str(scenario_id)), None)
                if detailed_match:
                    scenario = detailed_match
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