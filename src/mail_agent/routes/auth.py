from flask import Blueprint, redirect, url_for, session, request, current_app
from datetime import datetime
from mail_agent.app import MailAgentApp
from mail_agent.models import User, db
from authlib.integrations.flask_client import OAuth
from typing import cast


ca = cast(MailAgentApp, current_app)


# Create the blueprint
auth_bp = Blueprint('auth', __name__, url_prefix='')

@auth_bp.route('/login')
def login():
    """Route for handling login requests."""
    redirect_uri = url_for('auth.callback', _external=True)
    
    return ca.google.authorize_redirect(redirect_uri)

@auth_bp.route('/reauth')
def reauth():
    """Route for forcing re-authentication to get refresh token."""
    redirect_uri = url_for('auth.callback', _external=True)
    
    # Force consent to ensure we get a refresh token
    return ca.google.authorize_redirect(
        redirect_uri, 
        access_type='offline',
        prompt='consent'
    )

@auth_bp.route('/callback')
def callback():
    """Handle OAuth callback from Google."""
    token = ca.google.authorize_access_token()
    resp = ca.google.get('userinfo')
    user_info = resp.json()
    
    # Check if user exists, if not create a new user
    user = User.query.filter_by(email=user_info['email']).first()
    if not user:
        user = User( 
            name=user_info.get('name', ''), # type: ignore
            email=user_info['email'], # type: ignore
            google_id=user_info['id'] # type: ignore
        )
        db.session.add(user)
    
    # Store tokens for Gmail API access
    user.access_token = token.get('access_token')
    user.refresh_token = token.get('refresh_token')
    
    # If we got a new refresh token, store it
    if token.get('refresh_token'):
        user.refresh_token = token.get('refresh_token')
    
    # Set token expiry
    if token.get('expires_at'):
        user.token_expiry = datetime.fromtimestamp(token.get('expires_at'))
    
    db.session.commit()
    
    # Save user to session
    session['user_id'] = user.id
    return redirect('/')

@auth_bp.route('/logout')
def logout():
    """Handle user logout."""
    session.pop('user_id', None)
    return redirect('/')

@auth_bp.route('/update-instructions', methods=['POST'])
def update_instructions():
    """Update user processing instructions."""
    if 'user_id' not in session:
        return redirect('/login')
    
    instructions = request.form.get('instructions', '')
    user = User.query.get(session['user_id'])
    if user:
        user.processing_instructions = instructions
        user.updated_at = datetime.utcnow()
        db.session.commit()
    
    return redirect('/')
