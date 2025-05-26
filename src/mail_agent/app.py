from flask import Flask
from authlib.integrations.flask_client import OAuth
import os
import json
import re
from mail_agent.models import db
from pathlib import Path
from .config import Config
from .gmail import Gmail
from .ai.manager import LLMManager
from typing import List, Union, Any



class MailAgentApp(Flask):

    """
    MailAgentApp is a Flask application that serves as the main entry point for the Mail Agent application.
    It initializes the Flask app, configures it, and registers all routes and blueprints.
    """

    google: Any
    db: Any
    gmail: Gmail
    llm_manager: LLMManager

    def __init__(self, config_dir: str|Path = None, deployment: str = 'devel', *args, **kwargs):
        
        super().__init__(*args, **kwargs)

        self.secret_key = os.environ.get("SECRET_KEY") or os.urandom(24)
        
        # Default database URI, will be overridden by config if available
       
        self.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
        self.config["WTF_CSRF_ENABLED"] = True

        # Load configuration
        self.app_config = self.get_config(config_dir, deployment)
        
        # Update database URI from config if available
        if self.app_config and 'DATABASE_URI' in self.app_config:
            self.config["SQLALCHEMY_DATABASE_URI"] = self.app_config.DATABASE_URI
            # Ensure database directory exists
            self._ensure_db_directory_exists()
        else:
            raise ValueError("DATABASE_URI not found in configuration")
            
        # Initialize extensions
        db.init_app(self)
        
        # Register custom template filters
        self.register_template_filters()
        
        # Initialize LLM Manager
        self.llm_manager = LLMManager(self)
        
        self.register_oauth()

        # Create database tables
        with self.app_context():
            db.create_all()
        
        # Register routes
        self.register_routes()

        self.db = db
       

    def config_dir(self, config_dir: str | Path | None) -> Path:

        dirs = []

        if config_dir:
            dirs.append(config_dir)

        macd = os.getenv("MAIL_AGENT_CONFIG_DIR")

        if macd and Path(macd).exists():
            dirs.append(os.getenv("MAIL_AGENT_CONFIG_DIR"))

        if Path('/app/config').exists():
            dirs.append(Path('/app/config'))

        this_dir = Path(__file__).parents[2] / 'config'

        if this_dir.exists():
            dirs.append(this_dir)

        for path in dirs:
            if Path(path).exists():
                return Path(path);

        raise FileNotFoundError(f"Config directory not found in {dirs}")


    def get_config(self, config_dir: str | Path | None, deployment: str | None  = None) -> Config:

        config_dir = self.config_dir(config_dir)

        deployment = deployment or os.getenv("MAIL_AGENT_DEPLOY", "devel")

        self.appconfig  = Config.load(config_dir, deployment)

        client_secrets_name = self.appconfig['GOOGLE_CLIENT_SECRETS_FILE']

        if not client_secrets_name:
            raise FileNotFoundError(f"Google client secrets file not found in appconfig['GOOGLE_CLIENT_SECRETS_FILE'] {client_secrets_name}")

        csfp = self.appconfig.get_file_path(client_secrets_name)

        self.config['GOOGLE_CLIENT_SECRETS'] = json.loads(csfp.read_text())

        self.config.update(self.appconfig.to_dict())

        self.config['__APPCONFIG__'] = self.appconfig

        return self.appconfig

    def register_oauth(self):

        self.oauth = OAuth(self)

        self.oauth.init_app(self)

        self.google = self.oauth.register(
            name='google',
            client_id=self.config['GOOGLE_CLIENT_SECRETS']['web']['client_id'],
            client_secret=self.config['GOOGLE_CLIENT_SECRETS']['web']['client_secret'],
            access_token_url='https://accounts.google.com/o/oauth2/token',
            access_token_params=None,
            authorize_url='https://accounts.google.com/o/oauth2/auth',
            authorize_params=None,
            api_base_url='https://www.googleapis.com/oauth2/v1/',
            client_kwargs={
                'scope': 'openid email profile https://www.googleapis.com/auth/gmail.modify',
                'access_type': 'offline',
                'prompt': 'consent'
            },
            jwks_uri='https://www.googleapis.com/oauth2/v3/certs',
        )

    def register_template_filters(self):
        """Register custom Jinja template filters"""
        
        @self.template_filter('normalize_whitespace')
        def normalize_whitespace(text):
            """Convert all whitespace and runs of whitespace to single spaces"""
            if not text:
                return ''
            # Replace all whitespace characters with single spaces
            return re.sub(r'\s+', ' ', str(text)).strip()
    
    def register_routes(self):
        """Register all routes and blueprints with the app"""
    
        # Register blueprints
        from mail_agent.routes.auth import auth_bp
        from mail_agent.routes.instructions import instructions_bp
        from mail_agent.routes.main import main_bp
    
        self.register_blueprint(auth_bp)
        self.register_blueprint(instructions_bp)
        self.register_blueprint(main_bp)
            
    def _ensure_db_directory_exists(self):
        """Ensure the directory for the SQLite database exists and has correct permissions"""
        db_uri = self.config["SQLALCHEMY_DATABASE_URI"]
        
        # Only needed for SQLite databases
        if db_uri.startswith('sqlite:///'):
            # Extract the path from the URI
            db_path = db_uri.replace('sqlite:///', '')
            
            # If it's a relative path, make it absolute using the app's root_path
            if not os.path.isabs(db_path):
                db_path = os.path.join(self.root_path, db_path)
                
            # Create the directory if it doesn't exist
            db_dir = os.path.dirname(db_path)
            if not os.path.exists(db_dir):
                os.makedirs(db_dir, exist_ok=True)
                
            # Set appropriate permissions on the directory
            import stat
            os.chmod(db_dir, stat.S_IRWXU | stat.S_IRWXG | stat.S_IRWXO)  # 0777 permissions
            
            # If the database file exists, ensure it has write permissions
            if os.path.exists(db_path):
                os.chmod(db_path, stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IWGRP | stat.S_IROTH | stat.S_IWOTH)  # 0666 permissions
            


def init_app(config_dir=None) -> MailAgentApp:
    """
    Initialize and configure the Flask application
    
    Args:
        config_dir: Optional path to configuration directory. If not provided,
                   will look for config in the default location.
    
    Returns:
        Configured MailAgentApp instance
    """
    try:
        # If config_dir is not provided, it will be resolved within the MailAgentApp
        # The app uses several methods to find the config directory
        return MailAgentApp(config_dir=config_dir, import_name=__name__)
    except Exception as e:
        import sys
        print(f"Error initializing application: {str(e)}", file=sys.stderr)
        print("If this is related to database access, try running 'mactl db create' first", file=sys.stderr)
        raise    




if __name__ == '__main__':
    init_app().run(debug=True, port=5000)
