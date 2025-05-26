"""
Database management commands for Mail Agent CLI.
"""
import click
import os
import sys
from mail_agent.app import init_app, MailAgentApp
from mail_agent.models import db
from mail_agent.cli.utils import handle_exceptions
from mail_agent.cli.main import db_cmd


def _create_db(app: MailAgentApp) -> None:
    
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
            
            # Set appropriate permissions
            import stat
            try:
                os.chmod(db_dir, stat.S_IRWXU | stat.S_IRWXG | stat.S_IRWXO)  # 0777 permissions
                click.echo(f"Set directory permissions to 0777")
            except Exception as e:
                click.echo(f"Warning: Failed to set directory permissions: {e}", err=True)
            
    # Create the database tables
    with app.app_context():
        click.echo("Creating database tables...")
        db.create_all()
        click.echo("Database tables created successfully.")
    

@db_cmd.command('create')
@handle_exceptions
def create_db():
    """Create the database if it doesn't exist."""
    app = init_app()

    _create_db(app)



@db_cmd.command('recreate')
@click.option('--yes', is_flag=True, help='Skip confirmation prompt')
@handle_exceptions
def recreate_db(yes):
    """Delete and recreate the database."""
    if not yes and not click.confirm('This will delete all data in the database. Are you sure?'):
        click.echo("Operation cancelled.")
        return
        
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
    
   
    _create_db(app)
    click.echo("Database recreated successfully.")


@db_cmd.command('update-schema')
@handle_exceptions
def update_schema():
    """Update the database schema with timezone-aware columns."""
    app = init_app()
    
    with app.app_context():
        try:
            from datetime import timezone
            from sqlalchemy import text
            
            # For SQLite databases, we need to recreate the table
            db_uri = app.config.get('SQLALCHEMY_DATABASE_URI')
            if db_uri.startswith('sqlite:///'):
                click.echo("Updating SQLite database schema...")
                click.echo("WARNING: This operation will recreate tables. Make sure to backup your data first.")
                click.echo("For SQLite, the simplest way is to run 'mactl db recreate'")
                click.echo("Timezone issues will be fixed for new data.")
                return
                
            # For other databases, add timezone awareness to existing columns
            click.echo("Updating database schema for timezone awareness...")
            # The implementation depends on the specific database used
            # Here's a PostgreSQL example:
            if 'postgresql' in db_uri:
                conn = db.engine.connect()
                conn.execute(text("ALTER TABLE email ALTER COLUMN send_time TYPE TIMESTAMP WITH TIME ZONE"))
                conn.execute(text("ALTER TABLE email ALTER COLUMN created_at TYPE TIMESTAMP WITH TIME ZONE"))
                conn.execute(text("ALTER TABLE email ALTER COLUMN updated_at TYPE TIMESTAMP WITH TIME ZONE"))
                conn.close()
                click.echo("Database schema updated successfully.")
            else:
                click.echo(f"Schema update not implemented for this database type: {db_uri}")
                
        except Exception as e:
            click.echo(f"Error updating schema: {e}", err=True)
            click.echo("You may need to recreate the database with 'mactl db recreate'", err=True)
            sys.exit(1)
