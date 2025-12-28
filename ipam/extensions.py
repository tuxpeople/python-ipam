"""Flask extensions initialization."""

from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy

# Initialize extensions without app
db = SQLAlchemy()
migrate = Migrate()
limiter = Limiter(key_func=get_remote_address)
