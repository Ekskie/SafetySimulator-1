from app import app
from routes import *

# This is required for Vercel to find the app object
if __name__ == "__main__":
    app.run()