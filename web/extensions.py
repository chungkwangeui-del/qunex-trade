import os
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

# Get Redis URL from environment for rate limiter
# Falls back to memory:// for development
_redis_url = os.getenv("REDIS_URL", "memory://")
if not _redis_url or _redis_url.strip() == "":
    _redis_url = "memory://"

limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=_redis_url,
    storage_options={"socket_connect_timeout": 5} if _redis_url != "memory://" else {},
    strategy="fixed-window"  # More efficient for Redis
)
login_manager = LoginManager()
