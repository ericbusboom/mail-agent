"""
Utility functions for CLI exception handling and common operations.
"""
import sys
import traceback
import click
from functools import wraps
from typing import Callable, TypeVar, Any
from mail_agent.app import MailAgentApp
from mail_agent.models import User

# Type variables for function signatures
F = TypeVar('F', bound=Callable[..., Any])

def handle_exceptions(f: F) -> F:
    """
    A decorator for Click commands that handles exceptions and provides 
    consistent error reporting.
    
    Args:
        f: The Click command function to wrap
        
    Returns:
        The wrapped function with exception handling
    """
    @wraps(f)
    def wrapper(*args, **kwargs):

        ctx = click.get_current_context(silent=True)
        verbose = ctx and ctx.params.get('verbose', False)
        exceptions = ctx and ctx.params.get('exceptions', False)    

        if exceptions:
            # If exceptions are enabled, just call the function directly
            return f(*args, **kwargs)

        try:
            return f(*args, **kwargs)
        except click.Abort:
            # User aborted the command (e.g., with Ctrl+C)
            click.echo("\nOperation aborted by user.", err=True)
            sys.exit(130)  # Standard exit code for user interruption
        except click.UsageError as e:
            # Click usage errors (wrong parameters, etc.)
            click.echo(f"\nUsage error: {str(e)}", err=True)
            sys.exit(2)  # Standard exit code for usage errors
        except Exception as e:
            # All other exceptions
            click.echo(f"\nError: {str(e)}", err=True)
            
            # Check if verbose flag is set in the context

            if verbose:
                click.echo("\nTraceback:", err=True)
                traceback.print_exc()
            else:
                click.echo("\nFor more details, run with --verbose flag.", err=True)
                
            sys.exit(1)  # Standard exit code for general errors
            
    return wrapper  # type: ignore


def get_user_by_email(app: MailAgentApp, user_email: str) -> User:
    """
    Helper function to get user by email.
    
    Args:
        app: The MailAgentApp instance
        user_email: The email address of the user to find
        
    Returns:
        User: The found User object
        
    Raises:
        SystemExit: If the user is not found or has no valid token
    """
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
