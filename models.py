from flask_login import UserMixin

class User(UserMixin):
    def __init__(self, id, email=None):
        self.id = id
        self.email = email
        self.username = email.split('@')[0] if email else "User"

    # These are required by Flask-Login
    @property
    def is_active(self):
        return True

    @property
    def is_authenticated(self):
        return True

    @property
    def is_anonymous(self):
        return False

    def get_id(self):
        return str(self.id)