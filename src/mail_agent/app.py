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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.secret_key = os.environ.get("SECRET_KEY") or os.urandom(24)
        self.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///mail_agent.db"
        self.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
        self.config["WTF_CSRF_ENABLED"] = True

                # Initialize extensions
        db.init_app(self)
        
        # Register custom template filters
        self.register_template_filters()
        
        # Load configuration
        self.app_config = self.get_config(kwargs.get('config_dir', None))
        
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
            


def init_app() -> MailAgentApp:
    """Initialize and configure the Flask application"""
    
    # Initialize Flask app
    return MailAgentApp(__name__)




if __name__ == '__main__':
    init_app().run(debug=True, port=5000)
