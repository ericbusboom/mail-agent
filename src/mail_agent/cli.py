"""
Command Line Interface for Mail Agent
"""
import click
import pprint
import sys
from mail_agent.app import init_app, MailAgentApp
from mail_agent.models import User

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

@cli.group('mail')
def mail_cmd():
    """Gmail operations and management."""
    pass

def get_user_by_email(app: MailAgentApp, user_email: str) -> User:
    """Helper function to get user by email."""
    with app.app_context():
        # Find user
        if user_email:
            user = User.query.filter_by(email=user_email).first()
            if not user:
                click.echo(f"Error: User with email '{user_email}' not found.", err=True)
                sys.exit(1)
        else:
            # Use first user if no email specified
            user = User.query.first()
            if not user:
                click.echo("Error: No users found in database. Please login through the web interface first.", err=True)
                sys.exit(1)
        
        # Check if user has valid tokens
        if not user.access_token:
            click.echo(f"Error: User '{user.email}' has no valid access token. Please login through the web interface.", err=True)
            sys.exit(1)

    return user
        

@mail_cmd.command('list')
@click.option('--label', '-l', help='Filter emails by label name')
@click.option('--user-email', '-u', help='User email address (if not specified, uses first user)')
@click.option('--max-results', '-n', default=20, help='Maximum number of emails to retrieve (default: 20)')
def list_emails(label, user_email, max_results):
    """List emails in inbox or with specific label."""
    app = init_app()
    
    with app.app_context():
        user = get_user_by_email(app, user_email)
        
        try:
            from mail_agent.gmail import Gmail
            gmail = Gmail(app, user.id)
            
            if label:
                # List emails with specific label
                click.echo(f"Fetching emails with label '{label}' for user: {user.email}")
                emails = gmail.find_emails_with_label(label, max_results=max_results)
                
                if not emails:
                    click.echo(f"No emails found with label '{label}'")
                    return
                
                click.echo(f"\nFound {len(emails)} emails with label '{label}':")
            else:
                # List inbox emails
                click.echo(f"Fetching inbox emails for user: {user.email}")
                emails = gmail.read_inbox_emails(max_results=max_results)
                
                if not emails:
                    click.echo("No emails found in inbox")
                    return
                
                click.echo(f"\nFound {len(emails)} emails in inbox:")

        except Exception as e:
            click.echo(f"Error accessing Gmail: {str(e)}", err=True)
            click.echo("Make sure the user has properly authenticated through the web interface.", err=True)
            sys.exit(1)
            
        # Display emails
        click.echo("-" * 80)
        for i, email in enumerate(emails, 1):
            # Truncate long subject lines and sender names for better display
            subject = email.subject[:60] + "..." if len(email.subject) > 60 else email.subject
            sender = email.sender[:40] + "..." if len(email.sender) > 40 else email.sender
            
            # Format date
            date_str = email.date.strftime("%Y-%m-%d %H:%M") if email.date else "Unknown"
            
            click.echo(f"{i:3d}. From: {sender}")
            click.echo(f"     Subject: {subject}")
            click.echo(f"     Date: {date_str}")
            click.echo(f"     Labels: {', '.join(email.label_ids[:3])}{'...' if len(email.label_ids) > 3 else ''}")
            click.echo("-" * 80)
    


@mail_cmd.command('labels')
@click.option('--user-email', '-u', help='User email address (if not specified, uses first user)')
def list_labels(user_email):
    """List all available Gmail labels for a user."""
    app = init_app()
    
    with app.app_context():
        # Find user
        if user_email:
            user = User.query.filter_by(email=user_email).first()
            if not user:
                click.echo(f"Error: User with email '{user_email}' not found.", err=True)
                sys.exit(1)
        else:
            # Use first user if no email specified
            user = User.query.first()
            if not user:
                click.echo("Error: No users found in database. Please login through the web interface first.", err=True)
                sys.exit(1)
        
        # Check if user has valid tokens
        if not user.access_token:
            click.echo(f"Error: User '{user.email}' has no valid access token. Please login through the web interface.", err=True)
            sys.exit(1)
        
        try:
            from mail_agent.gmail import Gmail
            gmail = Gmail(app, user.id)
            labels = gmail.get_labels()
            
            if not labels:
                click.echo("No labels found")
                return
            
            click.echo(f"Available labels for user: {user.email}")
            click.echo("=" * 50)
            
            # Sort labels for better display
            sorted_labels = sorted(labels.items())
            
            for label_name, label_id in sorted_labels:
                click.echo(f"{label_name:<30} ({label_id})")
        
        except Exception as e:
            click.echo(f"Error accessing Gmail: {str(e)}", err=True)
            click.echo("Make sure the user has properly authenticated through the web interface.", err=True)
            sys.exit(1)
if __name__ == '__main__':
    cli()
