from flask import Blueprint, render_template, request, jsonify, redirect, url_for, session
from flask_login import login_user, logout_user, login_required, current_user
from models import User
from extensions import supabase

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

@auth_bp.route('/', methods=['GET'])
def auth():
    # Now this check will work without crashing
    if current_user.is_authenticated:
        if session.get('user_role') == 'admin':
            return redirect(url_for('admin.dashboard'))
        return redirect(url_for('general.index'))
    return render_template('auth/auth.html')

@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')

    try:
        # 1. Authenticate with Supabase Auth
        response = supabase.auth.sign_in_with_password({
            "email": email,
            "password": password
        })
        
        user_data = response.user
        if user_data:
            # 2. Fetch additional profile info
            profile_res = supabase.table('profiles').select('*').eq('id', user_data.id).execute()
            
            role = 'student'
            full_name = ''
            
            if profile_res.data:
                role = profile_res.data[0].get('role', 'student')
                full_name = profile_res.data[0].get('full_name', '')

            # 3. Create User Object for Flask-Login
            display_name = full_name if full_name else user_data.email.split('@')[0]
            
            user = User(
                id=user_data.id, 
                email=user_data.email, 
                role=role,
                username=display_name
            )
            
            # 4. CONNECT FLASK-LOGIN
            login_user(user)
            
            # 5. Set Backup Session Data
            session['user_role'] = role
            session['user'] = {
                'id': user_data.id,
                'email': user_data.email,
                'name': display_name,
                'role': role
            }

            target = url_for('admin.dashboard') if role == 'admin' else url_for('general.index')
            return jsonify({'success': True, 'redirect': target})
            
    except Exception as e:
        print(f"Login Error: {e}")
        return jsonify({'success': False, 'message': str(e)})

    return jsonify({'success': False, 'message': 'Invalid credentials'})

@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')
    full_name = data.get('full_name', '')

    try:
        # 1. Create Auth User
        # Note: If email confirmation is enabled in Supabase, this will send an email.
        response = supabase.auth.sign_up({
            "email": email,
            "password": password,
            "options": {
                "data": {
                    "full_name": full_name
                }
            }
        })
        
        # Check if user creation was successful
        # Note: response.user might be None if confirmation is required immediately depending on client version, 
        # but usually it returns the user object with 'identities' or confirmation_sent_at.
        if response.user:
            # 2. Sync Profile to Database
            # We insert the profile immediately so it's ready when they confirm and login.
            try:
                supabase.table('profiles').upsert({
                    'id': response.user.id,
                    'email': email,
                    'full_name': full_name,
                    'role': 'student'
                }).execute()
            except Exception as db_err:
                print(f"Profile creation warning: {db_err}")

            # CHANGED: Do NOT auto-login. 
            # Return success message telling user to verify email.
            # We are NOT setting session or calling login_user here.
            
            # If the user is already confirmed (e.g. Supabase setting is off), response.session would exist.
            # If response.session is None, it means email confirmation is required.
            if response.session is None:
                return jsonify({
                    'success': True, 
                    'message': 'Registration successful! Please check your email to verify your account before logging in.',
                    'redirect': None # Client JS should handle this by showing the message, not redirecting immediately
                })
            else:
                # Fallback: If your Supabase project has email auth DISABLED (auto-confirm ON),
                # then we can auto-login. But since you asked for verification, we assume it's ON.
                # However, for consistency, let's force them to login even if auto-confirmed.
                return jsonify({
                    'success': True, 
                    'message': 'Registration successful. Please log in.',
                    'redirect': None 
                })
            
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

    return jsonify({'success': False, 'message': 'Registration failed'})

@auth_bp.route('/logout')
@login_required
def logout():
    try:
        supabase.auth.sign_out()
    except Exception as e:
        print(f"Supabase signout warning: {e}")
        
    logout_user()
    session.clear()
    
    return redirect(url_for('auth.auth'))