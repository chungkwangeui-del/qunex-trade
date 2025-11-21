from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail
from flask_wtf.csrf import CSRFProtect
from flask_caching import Cache
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_login import LoginManager

# Initialize extensions
# db is initialized in web.database, but we can re-export it here if we want, 
# or just keep it there. For now, let's keep db in database.py to avoid breaking too many things.

mail = Mail()
csrf = CSRFProtect()
cache = Cache()
limiter = Limiter(key_func=get_remote_address, storage_uri="memory://")
login_manager = LoginManager()
