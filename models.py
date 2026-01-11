from flask_login import UserMixin
from extensions import supabase

class User(UserMixin):
    def __init__(self, id, email=None, role='student', username=None):
        self.id = id
        self.email = email
        self.role = role
        
        # Priority Logic for Username
        # 1. Use explicitly provided username
        if username and username.strip():
            self.username = username
        # 2. Fallback to email prefix
        elif email and '@' in email:
            try:
                self.username = email.split('@')[0]
            except:
                self.username = "Unknown"
        # 3. Last resort
        else:
            self.username = "Unknown"

    @staticmethod
    def get(user_id):
        """
        Static method to load user from Supabase.
        Used by Flask-Login's user_loader.
        """
        print(f"DEBUG: User.get() loading ID: {user_id}")
        
        try:
            # Query the 'profiles' table to get persistent user data
            response = supabase.table('profiles').select('*').eq('id', user_id).single().execute()
            
            if response.data:
                data = response.data
                # print(f"DEBUG: Data found: {data}") 
                
                return User(
                    id=data.get('id'),
                    email=data.get('email'),
                    role=data.get('role', 'student'),
                    # Ensure we pass the full_name here so it doesn't revert to email/unknown
                    username=data.get('full_name') 
                )
            
            print(f"DEBUG: No profile found for {user_id}")
            return None
            
        except Exception as e:
            print(f"ERROR: Failed to load user {user_id}: {e}")
            return None