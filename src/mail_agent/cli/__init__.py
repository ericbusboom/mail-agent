"""
Command Line Interface for Mail Agent.

This package contains all CLI-related functionality for the Mail Agent application.
"""
import click
from mail_agent.cli.utils import handle_exceptions
from mail_agent.cli.main import cli

# Import command modules to register them with Click
from mail_agent.cli import db
from mail_agent.cli import mail
from mail_agent.cli import config

# Make the CLI entrypoint available at the package level
__all__ = ['cli']
