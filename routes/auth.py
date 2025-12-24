from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for
from flask_login import login_user, logout_user, login_required, current_user
from models import User
from extensions import supabase
from gotrue.errors import AuthApiError

auth_bp = Blueprint('auth', __name__)

@auth_bp.route("/auth")
def auth():
    if current_user.is_authenticated:
        return redirect(url_for('general.index'))
    return render_template("auth.html")

@auth_bp.route("/auth/register", methods=['POST'])
def register():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')

    if not email or not password:
        return jsonify({'success': False, 'message': 'Missing email or password'}), 400

    try:
        response = supabase.auth.sign_up({
            "email": email, 
            "password": password
        })

        if response.user:
            return jsonify({
                'success': True, 
                'message': 'Registration successful. Please check your email to verify your account.'
            })
        else:
            return jsonify({'success': False, 'message': 'Registration failed.'}), 400

    except AuthApiError as e:
        return jsonify({'success': False, 'message': e.message}), 400
    except Exception as e:
        return jsonify({'success': False, 'message': f'System error: {str(e)}'}), 500

@auth_bp.route("/auth/login", methods=['POST'])
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
            
            # Fetch User Role for Session
            role = 'student'
            try:
                profile_res = supabase.table('profiles').select('role').eq('id', response.user.id).single().execute()
                if profile_res.data:
                    role = profile_res.data.get('role', 'student')
            except Exception as e:
                print(f"Error fetching role: {e}")

            session['supabase_token'] = response.session.access_token
            session['user_email'] = response.user.email
            session['user_role'] = role
            
            return jsonify({'success': True, 'message': 'Login successful'})

    except AuthApiError:
        return jsonify({'success': False, 'message': 'Invalid Login Credentials'}), 401
    except Exception as e:
        return jsonify({'success': False, 'message': f'System error: {str(e)}'}), 500

@auth_bp.route("/auth/logout")
@login_required
def logout():
    try:
        supabase.auth.sign_out()
    except:
        pass 
    logout_user()
    session.clear()
    return redirect(url_for('general.index'))

# --- API Helper Endpoints for Auth ---

@auth_bp.route("/api/update_email", methods=['POST'])
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

@auth_bp.route("/api/reset_password", methods=['POST'])
@login_required
def reset_password():
    data = request.get_json()
    new_password = data.get('password')
    
    try:
        if not new_password:
            supabase.auth.reset_password_email(current_user.email)
            return jsonify({'success': True, 'message': 'Reset link sent.'})
        
        supabase.auth.update_user({"password": new_password})
        return jsonify({'success': True, 'message': 'Password updated.'})
    except Exception as e:
         return jsonify({'success': False, 'message': str(e)}), 400