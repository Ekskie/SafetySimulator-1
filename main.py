import os
import logging
from flask import Flask, session
from flask_login import LoginManager
from extensions import supabase
from models import User

# Logging
logging.basicConfig(level=logging.DEBUG)

# Create App
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "safezard_secret_key")

# --- Login Manager ---
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'auth.auth' # Updated to point to blueprint

@login_manager.user_loader
def load_user(user_id):
    user_email = session.get('user_email')
    return User(user_id, email=user_email)

# --- Register Blueprints ---
from routes.general import general_bp
from routes.auth import auth_bp
from routes.student import student_bp
from routes.faculty import faculty_bp
from routes.admin import admin_bp

app.register_blueprint(general_bp)
app.register_blueprint(auth_bp)
app.register_blueprint(student_bp)
app.register_blueprint(faculty_bp)
app.register_blueprint(admin_bp)

if __name__ == "__main__":
    app.run(debug=True)