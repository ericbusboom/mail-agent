"""
Command Line Interface for Mail Agent
"""
import click
import pprint
from mail_agent.app import init_app

@click.group()
def cli():
    """Mail Agent CLI tool for configuration and management."""
    pass

@cli.command('config')
def config_cmd():
    """Display the application configuration."""
    app = init_app()
    click.echo("Mail Agent Configuration:")
    
    # Get all configuration items and convert to dictionary
    config_dict = dict(app.config.items())
    
    # Pretty print the configuration dictionary
    pp = pprint.PrettyPrinter(indent=4)
   
    for k, v in config_dict.items():
        if k.startswith('__'):
            print(f"{k}: {v}")
if __name__ == '__main__':
    cli()
