from flask import Blueprint, render_template, flash, redirect, url_for
from flask_login import login_required, current_user
from extensions import supabase
from utils import role_required

faculty_bp = Blueprint('faculty', __name__)

@faculty_bp.route("/faculty")
@login_required
@role_required('faculty')
def dashboard():
    try:
        # Fetch Profiles for Names/Emails
        profiles_response = supabase.table('profiles').select('id, email').execute()
        profiles_map = {p['id']: p['email'] for p in profiles_response.data}

        # Fetch Progress Data
        response = supabase.table('user_progress').select('*').execute()
        progress_data = response.data
        
        # Aggregate Data
        students_map = {}
        total_completions = 0
        total_score_sum = 0
        total_records = 0

        for record in progress_data:
            uid = record['user_id']
            if uid not in students_map:
                email = profiles_map.get(uid, "Unknown")
                name_display = email.split('@')[0].title() if '@' in email else uid[:8] + '...'
                
                students_map[uid] = {
                    'id': uid,
                    'name': name_display,
                    'email': email,
                    'active_count': 0,
                    'completed_count': 0,
                    'total_score': 0,
                    'last_active': record.get('created_at', '')[:10],
                    'scenarios': []
                }
            
            students_map[uid]['scenarios'].append({
                'title': record.get('scenario_id', 'Unknown'),
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
        print(f"Faculty Error: {e}")
        flash("System Error: Could not retrieve faculty data.", "error")
        return redirect(url_for('general.index'))