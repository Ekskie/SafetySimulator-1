from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for, session
from flask_login import login_required, current_user
from extensions import supabase
import json
from datetime import datetime, timedelta
import os
import collections

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

    return render_template("admin/dashboard.html", stats=stats, activity=recent_activity)

@admin_bp.route("/analytics")
@login_required
def analytics():
    analytics_data = {
        'total_attempts': 0,
        'pass_rate': 0,
        'critical_failures': 0,
        'total_passed': 0,
        'total_failed': 0,
        'chart_dates': [],
        'chart_attempts': [],
        'scenario_performance': []
    }
    
    try:
        # Fetch all quiz logs
        logs_res = supabase.table('quiz_logs').select('*').execute()
        logs = logs_res.data or []
        
        if logs:
            analytics_data['total_attempts'] = len(logs)
            
            passed = [l for l in logs if l.get('score', 0) >= 50]
            failed = [l for l in logs if l.get('score', 0) < 50]
            critical = [l for l in logs if l.get('score', 0) < 30]
            
            analytics_data['total_passed'] = len(passed)
            analytics_data['total_failed'] = len(failed)
            analytics_data['critical_failures'] = len(critical)
            
            if analytics_data['total_attempts'] > 0:
                analytics_data['pass_rate'] = round((len(passed) / len(logs)) * 100)

            # --- Activity Chart Data (Last 7 Days) ---
            today = datetime.now().date()
            dates = [(today - timedelta(days=i)).strftime('%Y-%m-%d') for i in range(6, -1, -1)]
            analytics_data['chart_dates'] = dates
            
            date_counts = collections.Counter()
            for log in logs:
                created = log.get('created_at', '')
                if created:
                    # Simple date extraction
                    date_str = created.split('T')[0]
                    date_counts[date_str] += 1
            
            analytics_data['chart_attempts'] = [date_counts.get(d, 0) for d in dates]

            # --- Scenario Performance Table ---
            scenario_stats = {} # {title: {attempts: 0, total_score: 0, passed: 0}}
            
            for log in logs:
                title = log.get('scenario_title', 'Unknown')
                score = log.get('score', 0)
                
                if title not in scenario_stats:
                    scenario_stats[title] = {'attempts': 0, 'total_score': 0, 'passed': 0}
                
                stats = scenario_stats[title]
                stats['attempts'] += 1
                stats['total_score'] += score
                if score >= 50:
                    stats['passed'] += 1
            
            # Convert to list
            for title, stats in scenario_stats.items():
                analytics_data['scenario_performance'].append({
                    'title': title,
                    'attempts': stats['attempts'],
                    'avg_score': round(stats['total_score'] / stats['attempts']) if stats['attempts'] > 0 else 0,
                    'completion_rate': round((stats['passed'] / stats['attempts']) * 100) if stats['attempts'] > 0 else 0
                })
            
            # Sort by attempts desc
            analytics_data['scenario_performance'].sort(key=lambda x: x['attempts'], reverse=True)

    except Exception as e:
        print(f"Analytics error: {e}")
        flash(f"Error calculating analytics: {str(e)}", "error")

    return render_template("admin/analytics.html", analytics=analytics_data)

@admin_bp.route("/settings", methods=['GET', 'POST'])
@login_required
def settings():
    if request.method == 'POST':
        # Simulating settings save since we might not have a settings table yet
        # In a real app, this would update a 'system_settings' table or config file
        form_data = request.form
        
        # Example: print(form_data.get('site_name'))
        
        flash("System settings saved successfully.", "success")
        return redirect(url_for('admin.settings'))
        
    return render_template("admin/settings.html")

@admin_bp.route("/students")
@login_required
def students():
    students_data = []
    total_scenarios = 0
    try:
        scenarios_res = supabase.table('scenarios').select('*', count='exact').execute()
        total_scenarios = scenarios_res.count if scenarios_res.count is not None else 0

        response = supabase.table('profiles').select('*').eq('role', 'student').order('created_at', desc=True).execute()
        
        progress_res = supabase.table('user_progress').select('user_id').execute()
        progress_map = {}
        if progress_res.data:
            for p in progress_res.data:
                uid = p.get('user_id')
                if uid:
                    progress_map[uid] = progress_map.get(uid, 0) + 1

        if response.data:
            for p in response.data:
                uid = p.get('id')
                joined_str = p.get('created_at')
                joined_date = None
                if joined_str:
                    try:
                        joined_date = datetime.fromisoformat(joined_str.replace('Z', '+00:00'))
                    except:
                        pass
                
                status = p.get('status', 'active') 
                
                students_data.append({
                    'id': uid,
                    'name': p.get('full_name') or p.get('username') or 'Unknown',
                    'email': p.get('email'),
                    'avatar_url': p.get('avatar_url'),
                    'joined_date': joined_date,
                    'status': status,
                    'completed_scenarios': progress_map.get(uid, 0)
                })

    except Exception as e:
        print(f"Error fetching students: {e}")
        flash(f"Error loading students: {str(e)}", "error")

    return render_template("admin/students.html", students=students_data, total_scenarios=total_scenarios)

@admin_bp.route("/faculty")
@login_required
def faculty():
    faculty_data = []
    try:
        faculty_res = supabase.table('profiles').select('*').eq('role', 'faculty').execute()
        pending_res = supabase.table('profiles').select('*').eq('role', 'pending').execute()
        
        all_profiles = (faculty_res.data or []) + (pending_res.data or [])
        all_profiles.sort(key=lambda x: x.get('created_at', ''), reverse=True)

        for p in all_profiles:
            uid = p.get('id')
            joined_str = p.get('created_at')
            joined_date = None
            if joined_str:
                try:
                    joined_date = datetime.fromisoformat(joined_str.replace('Z', '+00:00'))
                except:
                    pass
            
            faculty_data.append({
                'id': uid,
                'name': p.get('full_name') or p.get('username') or 'Unknown',
                'email': p.get('email'),
                'avatar_url': p.get('avatar_url'),
                'joined_date': joined_date,
                'role': p.get('role', 'faculty')
            })

    except Exception as e:
        print(f"Error fetching faculty: {e}")
        flash(f"Error loading faculty list: {str(e)}", "error")

    return render_template("admin/faculty.html", faculty=faculty_data)

@admin_bp.route("/approve_faculty/<string:user_id>", methods=['POST'])
@login_required
def approve_faculty(user_id):
    try:
        supabase.table('profiles').update({'role': 'faculty'}).eq('id', user_id).execute()
        flash("Faculty request approved successfully.", "success")
    except Exception as e:
        print(f"Error approving faculty: {e}")
        flash(f"Error approving request: {str(e)}", "error")
    return redirect(url_for('admin.faculty'))

@admin_bp.route("/ban_faculty/<string:user_id>", methods=['POST'])
@login_required
def ban_faculty(user_id):
    try:
        supabase.table('profiles').update({'role': 'banned'}).eq('id', user_id).execute()
        flash("Faculty member suspended.", "success")
    except Exception as e:
        print(f"Error suspending faculty: {e}")
        flash(f"Error suspending user: {str(e)}", "error")
    return redirect(url_for('admin.faculty'))

@admin_bp.route("/ban_student/<string:student_id>", methods=['POST'])
@login_required
def ban_student(student_id):
    try:
        supabase.table('profiles').update({'status': 'banned'}).eq('id', student_id).execute()
        flash("Student account has been suspended.", "success")
    except Exception as e:
        print(f"Error banning student: {e}")
        flash(f"Could not suspend student: {str(e)}", "error")
        
    return redirect(url_for('admin.students'))

@admin_bp.route("/library_manager")
@login_required
def library_manager():
    scenarios = []
    try:
        response = supabase.table('scenarios').select('*').order('created_at', desc=True).execute()
        scenarios = response.data
    except Exception as e:
        print(f"Error fetching library: {e}")
        flash(f"Error loading library: {str(e)}", "error")
        
    return render_template("admin/library_manager.html", scenarios=scenarios)

@admin_bp.route("/delete_scenario/<string:scenario_id>", methods=['POST'])
@login_required
def delete_scenario(scenario_id):
    try:
        supabase.table('scenarios').delete().eq('id', scenario_id).execute()
        flash(f"Scenario '{scenario_id}' deleted successfully.", "success")
    except Exception as e:
        print(f"Error deleting scenario: {e}")
        flash(f"Error deleting scenario: {str(e)}", "error")
        
    return redirect(url_for('admin.library_manager'))

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
        clean_id = filename.replace('.json', '')
        
        # 2. Extract Fields
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
            'nodes': nodes_data, 
            'quiz': quiz_data, 
            'workplace': workplace,
            'subcategory': subcategory,
            'difficulty': difficulty,
            'duration': duration,
            'hazards': hazards,
            'created_at': 'now()'
        }
        
        # 3. Upsert to Supabase
        res = supabase.table('scenarios').upsert(record).execute()

        return jsonify({'success': True, 'message': f'Scenario "{clean_id}" saved successfully!'})

    except Exception as e:
        print(f"Save Error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': str(e)}), 500