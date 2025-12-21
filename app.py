import os
import logging
from flask import Flask, session
from flask_login import LoginManager
from supabase import create_client, Client
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.DEBUG)

# Create the app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "safezard_secret_key")

# --- Supabase Configuration ---
# OPTION 1: Using .env file (Recommended)
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("Supabase URL and Key are missing. Check your .env file.")

# Initialize Supabase Client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- Login Manager Configuration ---
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'auth'

# User Loader for Flask-Login
@login_manager.user_loader
def load_user(user_id):
    # Important: Ensure models.py is updated to the version without SQLAlchemy
    from models import User
    # Retrieve email from session if available to populate user details
    user_email = session.get('user_email')
    return User(user_id, email=user_email)