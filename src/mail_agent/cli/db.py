"""
Database management commands for Mail Agent CLI.
"""
import click
import os
import sys
from mail_agent.app import init_app
from mail_agent.models import db
from mail_agent.cli.utils import handle_exceptions
from mail_agent.cli.main import db_cmd

@db_cmd.command('create')
@handle_exceptions
def create_db():
    """Create the database if it doesn't exist."""
    app = init_app()
    db_uri = app.config.get('SQLALCHEMY_DATABASE_URI')
    
    click.echo(f"Using database: {db_uri}")
    
    # For SQLite, create the directory if it doesn't exist
    if db_uri.startswith('sqlite:///'):
        # Extract the path from the URI
        db_path = db_uri.replace('sqlite:///', '')
        
        # If it's a relative path, make it absolute using the app's root_path
        if not os.path.isabs(db_path):
            db_path = os.path.join(app.root_path, db_path)
            
        # Create the directory if it doesn't exist
        db_dir = os.path.dirname(db_path)
        if not os.path.exists(db_dir):
            click.echo(f"Creating directory: {db_dir}")
            os.makedirs(db_dir, exist_ok=True)
            
    # Create the database tables
    with app.app_context():
        click.echo("Creating database tables...")
        db.create_all()
        click.echo("Database tables created successfully.")


@db_cmd.command('recreate')
@click.confirmation_option(prompt='This will delete all data in the database. Are you sure?')
@handle_exceptions
def recreate_db():
    """Delete and recreate the database."""
    app = init_app()
    db_uri = app.config.get('SQLALCHEMY_DATABASE_URI')
    
    click.echo(f"Using database: {db_uri}")
    
    # For SQLite, delete the file
    if db_uri.startswith('sqlite:///'):
        # Extract the path from the URI
        db_path = db_uri.replace('sqlite:///', '')
        
        # If it's a relative path, make it absolute using the app's root_path
        if not os.path.isabs(db_path):
            db_path = os.path.join(app.root_path, db_path)
            
        # Delete the file if it exists
        if os.path.exists(db_path):
            click.echo(f"Deleting database file: {db_path}")
            os.remove(db_path)
    else:
        # For other databases, drop all tables
        with app.app_context():
            click.echo("Dropping all tables...")
            db.drop_all()
    
    # Create the database
    create_db()
    click.echo("Database recreated successfully.")
