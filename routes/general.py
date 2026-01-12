from flask import Blueprint, render_template
from extensions import supabase

general_bp = Blueprint('general', __name__)

@general_bp.route("/")
def index():
    scenario_count = 0
    system_status = "OFFLINE"
    status_color = "text-danger"

    try:
        # Check connection and get exact count of scenarios
        # We perform a lightweight query to check connectivity and count
        res = supabase.table('scenarios').select('id', count='exact').execute()
        
        # If we get a response, the system is online
        system_status = "ONLINE"
        status_color = "text-success"
        
        # Determine the count from the response
        if res.count is not None:
            scenario_count = res.count
        elif res.data:
            scenario_count = len(res.data)
            
    except Exception as e:
        print(f"Stats Error: {e}")
        # Defaults (OFFLINE/0) are already set above
        
    return render_template("index.html", 
                         scenario_count=scenario_count, 
                         system_status=system_status,
                         status_color=status_color)

@general_bp.route("/tutorial")
def tutorial():
    return render_template("tutorial.html")

@general_bp.route("/about")
def about():
    return render_template("about.html")