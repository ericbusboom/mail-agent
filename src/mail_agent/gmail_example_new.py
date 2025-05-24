#!/usr/bin/env python3
"""
Example script demonstrating the refactored Gmail API usage.

This shows how to use the new Gmail class constructor that takes both
app and user_id, eliminating the need to pass user_id to every method.
"""

from mail_agent.app import init_app
from mail_agent.cli import get_user_by_email
from mail_agent.gmail import Gmail

def main():
    """Demonstrate Gmail API usage with the new constructor pattern."""
    
    # Initialize the app
    app = init_app()
    
    with app.app_context():
        # Get the user (uses first user if no email specified)
        user = get_user_by_email(app, '')
        print(f"Working with user: {user.email}")
        
        # Create Gmail instance with app and user_id
        # This is the new pattern - Gmail is constructed with user context
        gmail = Gmail(app, user.id)
        
        # Now all methods work without needing user_id parameter
        print("\n=== Available Labels ===")
        labels = gmail.get_labels()
        for name, label_id in sorted(labels.items())[:5]:  # Show first 5 labels
            print(f"  {name:<20} ({label_id})")
        
        print("\n=== Recent Inbox Emails ===")
        emails = gmail.read_inbox_emails(max_results=3)
        for i, email in enumerate(emails, 1):
            print(f"  {i}. From: {email.sender[:40]}")
            print(f"     Subject: {email.subject[:50]}")
            print(f"     Date: {email.date.strftime('%Y-%m-%d %H:%M') if email.date else 'Unknown'}")
            print()
        
        print("=== Emails with 'IMPORTANT' Label ===")
        important_emails = gmail.find_emails_with_label("IMPORTANT", max_results=2)
        if important_emails:
            for i, email in enumerate(important_emails, 1):
                print(f"  {i}. {email.subject[:60]}")
        else:
            print("  No important emails found")
        
        print(f"\n=== Summary ===")
        print(f"Total labels: {len(labels)}")
        print(f"Recent inbox emails: {len(emails)}")
        print(f"Important emails: {len(important_emails)}")
        
        print("\n✅ Gmail API refactoring successful!")
        print("📧 All methods now work without user_id parameter")

if __name__ == "__main__":
    main()
