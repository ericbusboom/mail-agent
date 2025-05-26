"""
Gmail/mail operations commands for Mail Agent CLI.
"""
import click
import sys
import json
from mail_agent.app import init_app
from mail_agent.models import User, db, Email
from mail_agent.gmail import Gmail
from mail_agent.cli.utils import handle_exceptions, get_user_by_email
from mail_agent.cli.main import mail_cmd

from typing import List, Optional

@mail_cmd.command('list')
@click.option('--label', '-l', help='Filter emails by label name')
@click.option('--user-email', '-u', help='User email address (if not specified, uses first user)')
@click.option('--max-results', '-n', default=20, help='Maximum number of emails to retrieve (default: 20)')
@handle_exceptions
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
@handle_exceptions
def list_labels(user_email):
    """List all available Gmail labels for a user."""
    app = init_app()
    
    with app.app_context():
        user = get_user_by_email(app, user_email)
        
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


@mail_cmd.command('store')
@click.option('--user-email', '-u', help='User email address (if not specified, uses first user)')
@click.option('--max-results', '-n', default=1000, help='Maximum number of emails to retrieve if no previous emails exist (default: 1000)')
@click.option('--force-full', '-f', is_flag=True, help='Force fetching the maximum number of emails regardless of existing data')
@handle_exceptions
def store_emails(user_email, max_results, force_full):
    """Download emails and store them in the database."""
    app = init_app()
    
    with app.app_context():
        user = get_user_by_email(app, user_email)
        
        try:
            from mail_agent.gmail import Gmail
            gmail = Gmail(app, user.id)
            
            # Check if we have existing emails for this user
            if not force_full:
                latest_email = Email.query.filter_by(user_id=user.id).order_by(Email.send_time.desc()).first()
            else:
                latest_email = None
                
            if latest_email and not force_full:
                click.echo(f"Found existing emails. Fetching emails newer than {latest_email.send_time}")
                # In a more robust implementation, we would use the date to create a Gmail query
                # For now, we'll just fetch all and filter
                emails = gmail.fetch_all(max_results=max_results)
                # Filter emails that are newer than our latest email
                new_emails = []
                for e in emails:
                    # Make sure both dates have timezone information
                    if e.date and latest_email.send_time:
                        # Make latest_email.send_time timezone-aware if it's not
                        from datetime import timezone
                        latest_time = latest_email.send_time
                        if latest_time.tzinfo is None:
                            latest_time = latest_time.replace(tzinfo=timezone.utc)
                            
                        # Now we can safely compare
                        if e.date > latest_time:
                            new_emails.append(e)
                    elif not e.date:
                        # For emails with no date, we'll include them to be safe
                        click.echo(f"Warning: Email with ID {e.id} has no date, including it anyway")
                        new_emails.append(e)
                click.echo(f"Found {len(new_emails)} new emails to store (out of {len(emails)} fetched)")
                emails_to_store = new_emails
            else:
                click.echo(f"No existing emails found or full sync requested. Fetching up to {max_results} emails.")
                emails_to_store = gmail.fetch_all(max_results=max_results)
                click.echo(f"Found {len(emails_to_store)} emails to store")
            
            # Store emails in the database
            if not emails_to_store:
                click.echo("No new emails to store.")
                return
            
            click.echo("Storing emails in the database...")
            
            # Use a progress bar for better UX
            with click.progressbar(emails_to_store, label='Storing emails') as bar:
                for gmail_message in bar:
                    try:
                        # Check if the email body is empty and log it
                        if not gmail_message.body_text:
                            click.echo(f"Warning: Email with ID {gmail_message.id} has empty body")
                        
                        # Create or update email in the database
                        email_model = Email.create_or_update_from_gmail(gmail_message, user.id)
                        
                        # Add to session if it's a new email
                        if email_model not in db.session:
                            db.session.add(email_model)
                        
                        # Commit in batches to avoid performance issues
                        if bar.pos % 50 == 0:
                            db.session.commit()
                    except Exception as e:
                        click.echo(f"Error processing email {gmail_message.id}: {e}", err=True)
                        continue
            
            # Final commit for any remaining emails
            db.session.commit()
            
            click.echo(f"Successfully stored {len(emails_to_store)} emails in the database.")
            
        except Exception as e:
            click.echo(f"Error storing emails: {str(e)}", err=True)
            db.session.rollback()
            sys.exit(1)


@mail_cmd.command('view')
@click.option('--user-email', '-u', help='User email address (if not specified, uses first user)')
@click.option('--id', help='Email ID to view details for')
@click.option('--list-only', '-l', is_flag=True, help='Only list emails without showing bodies')
@click.option('--limit', default=10, help='Number of emails to list (default: 10)')
@handle_exceptions
def view_emails(user_email, id, list_only, limit):
    """View emails stored in the database."""
    app = init_app()
    
    with app.app_context():
        user = get_user_by_email(app, user_email)
        
        if id:
            # View a specific email
            email = Email.query.filter_by(id=id, user_id=user.id).first()
            if not email:
                click.echo(f"Email with ID {id} not found for user {user.email}")
                return
                
            click.echo(f"Email ID: {email.id}")
            click.echo(f"Thread ID: {email.thread_id}")
            click.echo(f"Date: {email.send_time}")
            click.echo(f"From: {email.from_address}")
            click.echo(f"To: {email.to_address}")
            click.echo(f"Subject: {email.subject}")
            click.echo(f"Labels: {email.labels}")
            click.echo(f"Snippet: {email.snippet}")
            
            if email.analysis:
                click.echo("\nAI Analysis:")
                try:
                    # Try to parse JSON for pretty display
                
                    analysis_data = json.loads(email.analysis)
                    for key, value in analysis_data.items():
                        if isinstance(value, list):
                            click.echo(f"  {key}: {', '.join(value)}")
                        else:
                            click.echo(f"  {key}: {value}")
                except json.JSONDecodeError:
                    # If not valid JSON, display as plain text
                    click.echo(email.analysis)
            
            if not list_only:
                click.echo("\nBody:")
                if email.body:
                    # If body is very long, truncate it
                    if len(email.body) > 1000:
                        click.echo(f"{email.body[:1000]}...\n[truncated, {len(email.body)} total characters]")
                    else:
                        click.echo(email.body)
                else:
                    click.echo("[Empty body]")
        else:
            # List emails
            emails = Email.query.filter_by(user_id=user.id).order_by(Email.send_time.desc()).limit(limit).all()
            
            if not emails:
                click.echo(f"No emails found for user {user.email}")
                return
                
            click.echo(f"Found {len(emails)} emails for user {user.email}:")
            click.echo("-" * 80)
            
            for i, email in enumerate(emails, 1):
                # Truncate long subject lines and sender names for better display
                subject = email.subject[:60] + "..." if len(email.subject) > 60 else email.subject
                sender = email.from_address[:40] + "..." if len(email.from_address) > 40 else email.from_address
                
                # Format date
                date_str = email.send_time.strftime("%Y-%m-%d %H:%M") if email.send_time else "Unknown"
                
                # Check if body is empty
                body_status = "[Empty]" if not email.body else f"[{len(email.body)} chars]"
                
                if email.analysis:
        
                    analysis = json.loads(email.analysis.strip('```')) if email.analysis else {}
                   
                else:
                    analysis = {}

                from textwrap import indent

                click.echo(f"{i:3d}. ID: {email.id}")
                click.echo(f"    From: {sender}")
                click.echo(f"    Subject: {subject}")
                click.echo(f"    Date: {date_str}")
                click.echo(f"    Body: {body_status}")
                if analysis:
                    click.echo(f"    Analysis:")
                    click.echo(indent(json.dumps(analysis, indent=2), ' ' * 6))


                click.echo("-" * 80)
                
            click.echo(f"\nTo view a specific email, use: mactl mail view --id <email_id>")


@mail_cmd.command('delete')
@handle_exceptions
def delete():
    """Delete all emails from the database."""
    app = init_app()
    
    with app.app_context():
        click.echo("This will delete ALL emails from the database. Are you sure?")
        if not click.confirm("Do you want to proceed?", default=False):
            click.echo("Operation cancelled.")
            return
        
        try:
            # Delete all emails
            Email.query.delete()
            db.session.commit()
            click.echo("All emails deleted successfully.")
        except Exception as e:
            click.echo(f"Error deleting emails: {str(e)}", err=True)
            db.session.rollback()
            sys.exit(1)


@mail_cmd.command('analyze')
@click.option('--user-email', '-u', help='User email address (if not specified, uses first user)')
@click.option('--limit', default=100, help='Maximum number of emails to analyze (default: 10)')
@click.option('--force', '-f', is_flag=True, help='Force re-analysis of already analyzed emails')
@handle_exceptions
def analyze_emails(user_email, limit, force):
    """Analyze emails in the database using AI."""
    app = init_app()
    
    with app.app_context():
        user = get_user_by_email(app, user_email)
        
        # Query for emails without analysis or with force flag
        if force:
            query = Email.query.filter_by(user_id=user.id)
        else:
            query = Email.query.filter_by(user_id=user.id).filter(
                (Email.analysis.is_(None)) | (Email.analysis == '')
            )
        
        # Get emails to analyze
        emails: List[Email] = query.order_by(Email.send_time.desc()).limit(limit).all()
        
        if not emails:
            click.echo(f"No emails found to analyze for user {user.email}")
            return
        
        click.echo(f"Analyzing {len(emails)} emails for user {user.email}...")
        
        # Initialize LLM manager
        from mail_agent.ai.manager import LLMManager
        llm_manager = LLMManager(app)
        
        # Process emails in batches to avoid token limits
        batch_size = 1  # Process one email at a time for detailed analysis
        
        with click.progressbar(range(0, len(emails), batch_size), 
                               label='Analyzing emails') as bar:
            for i in bar:
                batch = emails[i:i + batch_size]
                
                try:
                    # Create prompt using email_analysis template directly with Email objects
                    prompt = llm_manager.create_document(
                        messages=batch,
                        template_name="email_analysis"
                    )
                    
                    # Send to LLM
                    response = llm_manager.send_request(prompt)
                    
                    # Update the database with the analysis results
                    for email in batch:
                        # Store the analysis in the database
                        email.analysis = response
                        db.session.add(email)
                        
                        # Commit after each email to avoid losing all work if there's an error
                        db.session.commit()
                        
                except Exception as e:
                    click.echo(f"\nError analyzing batch starting at email {i+1}: {str(e)}", err=True)
                    db.session.rollback()
                    continue
        
        click.echo(f"Successfully analyzed {len(emails)} emails.")
        click.echo("To view analysis results, use: mactl mail view --id <email_id>")
