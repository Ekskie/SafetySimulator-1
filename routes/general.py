from flask import Blueprint, render_template

# Create Blueprint
general_bp = Blueprint('general', __name__)

@general_bp.route("/")
def index():
    return render_template("index.html")

@general_bp.route("/tutorial")
def tutorial():
    return render_template("tutorial.html")

@general_bp.route("/about")
def about():
    return render_template("about.html")