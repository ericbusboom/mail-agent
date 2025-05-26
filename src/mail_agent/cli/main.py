"""
Main CLI entrypoint and command group definitions.
"""
import click
from mail_agent.cli.utils import handle_exceptions

@click.group()
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose output for errors')
@click.pass_context
def cli(ctx, verbose):
    """Mail Agent CLI tool for configuration and management."""
    # Store verbose flag in the context for access in subcommands
    ctx.ensure_object(dict)
    ctx.obj['verbose'] = verbose


@cli.group('mail')
def mail_cmd():
    """Gmail operations and management."""
    pass


@cli.group('db')
def db_cmd():
    """Database operations and management."""
    pass
