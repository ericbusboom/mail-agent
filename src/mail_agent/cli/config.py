"""
Configuration commands for Mail Agent CLI.
"""
import click
import pprint
import sys
from mail_agent.app import init_app
from mail_agent.cli.utils import handle_exceptions
from mail_agent.cli.main import cli

@cli.command('config')
@handle_exceptions
def config_cmd():
    """Display the application configuration."""

    try:
        app = init_app()
    except Exception as e:
        click.echo(f"Error initializing application: {str(e)}", err=True)
        sys.exit(1)
        
    click.echo("Mail Agent Configuration:")
    
    # Get all configuration items and convert to dictionary
    config_dict = dict(app.config.items())
    
    # Extract the database URI
    db_uri = config_dict.get('SQLALCHEMY_DATABASE_URI', 'Not configured')
    
    # Show important configuration values
    click.echo("\nDatabase Location:")
    click.echo(f"  {db_uri}")
    
    # Show loaded configuration files
    if app.app_config and hasattr(app.app_config, '__loaded_files__'):
        click.echo("\nLoaded Configuration Files:")
        for file_path in app.app_config.__loaded_files__:
            click.echo(f"  {file_path}")
    
    click.echo("\nDetailed Configuration:")
    pp = pprint.PrettyPrinter(indent=2)
    filtered_config = {k: v for k, v in app.app_config.items() 
                       if not k.startswith('_') and not isinstance(v, (dict, list, set, tuple))}
    pp.pprint(filtered_config)
