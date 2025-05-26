#!/usr/bin/env python3
"""
Advanced example showing LLMManager with Gmail integration.
"""

import sys
from pathlib import Path

# Add the src directory to the path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from mail_agent.app import MailAgentApp
from mail_agent.gmail import Gmail, GmailMessage


def create_sample_messages():
    """Create sample Gmail messages for testing."""
    sample_data = [
        {
            'id': '1',
            'threadId': 'thread1',
            'labelIds': ['INBOX'],
            'snippet': 'Meeting tomorrow at 2pm',
            'payload': {
                'headers': [
                    {'name': 'From', 'value': 'boss@company.com'},
                    {'name': 'To', 'value': 'me@company.com'},
                    {'name': 'Subject', 'value': 'Team Meeting Tomorrow'},
                    {'name': 'Date', 'value': 'Wed, 25 May 2025 10:00:00 +0000'}
                ],
                'body': {'data': 'SGV5IGV2ZXJ5b25lLCBEb24ndCBmb3JnZXQgd2UgaGF2ZSBvdXIgdGVhbSBtZWV0aW5nIHRvbW9ycm93IGF0IDJwbSBpbiB0aGUgY29uZmVyZW5jZSByb29tLiBQbGVhc2UgYnJpbmcgeW91ciBwcm9qZWN0IHVwZGF0ZXMu'}
            }
        },
        {
            'id': '2',
            'threadId': 'thread2',
            'labelIds': ['INBOX'],
            'snippet': 'Invoice #12345 due soon',
            'payload': {
                'headers': [
                    {'name': 'From', 'value': 'billing@vendor.com'},
                    {'name': 'To', 'value': 'me@company.com'},
                    {'name': 'Subject', 'value': 'Invoice #12345 - Payment Due'},
                    {'name': 'Date', 'value': 'Thu, 26 May 2025 09:30:00 +0000'}
                ],
                'body': {'data': 'VGhpcyBpcyBhIHJlbWluZGVyIHRoYXQgeW91ciBpbnZvaWNlICMxMjM0NSBmb3IgJDUwMCBpcyBkdWUgb24gSnVuZSAxc3QuIFBsZWFzZSBwcm9jZXNzIHBheW1lbnQgYXQgeW91ciBlYXJsaWVzdCBjb252ZW5pZW5jZS4='}
            }
        },
        {
            'id': '3',
            'threadId': 'thread3',
            'labelIds': ['INBOX'],
            'snippet': 'Newsletter: AI trends this week',
            'payload': {
                'headers': [
                    {'name': 'From', 'value': 'newsletter@techblog.com'},
                    {'name': 'To', 'value': 'me@company.com'},
                    {'name': 'Subject', 'value': 'Weekly AI Newsletter - Latest Trends'},
                    {'name': 'Date', 'value': 'Fri, 27 May 2025 08:00:00 +0000'}
                ],
                'body': {'data': 'VGhpcyB3ZWVrIGluIEFJOiBPcGVuQUkgcmVsZWFzZXMgbmV3IG1vZGVsLCBHb29nbGUgdXBkYXRlcyBCYXJkLCBhbmQgQW50aHJvcGljIGltcHJvdmVzIENsYXVkZS4gQWxzbyBpbmNsdWRlZDogYmVzdCBwcmFjdGljZXMgZm9yIEFJIGluIGJ1c2luZXNzLg=='}
            }
        }
    ]
    
    messages = []
    for data in sample_data:
        messages.append(GmailMessage(data))
    
    return messages


def demo_advanced_llm():
    """Demonstrate advanced LLMManager functionality with sample messages."""
    
    app = MailAgentApp(__name__)
    
    with app.app_context():
        print("=== Advanced LLMManager Demo ===")
        
        llm_manager = app.llm_manager
        
        # Create sample messages
        messages = create_sample_messages()
        print(f"Created {len(messages)} sample messages")
        
        print("\nSample messages:")
        for i, msg in enumerate(messages, 1):
            print(f"  {i}. From: {msg.sender}")
            print(f"     Subject: {msg.subject}")
            print(f"     Snippet: {msg.snippet}")
            print()
        
        # Demo 1: Topic extraction using LLM
        print("=== Topic Extraction with LLM ===")
        try:
            topics = llm_manager.extract_topics_llm(messages)
            print(f"✓ Extracted {len(topics)} topics")
            for topic in topics:
                print(f"  - {topic.get('name', 'Unknown')}: {topic.get('description', 'No description')}")
        except Exception as e:
            print(f"✗ Topic extraction failed: {e}")
        
        # Demo 2: Topic extraction using KNN
        print(f"\n=== Topic Extraction with KNN ===")
        try:
            topics_knn = llm_manager.extract_topics_knn(messages, n_topics=2)
            print(f"✓ Extracted {len(topics_knn)} topics using KNN")
            for topic in topics_knn:
                print(f"  - {topic.get('name', 'Unknown')}")
                print(f"    Description: {topic.get('description', 'No description')}")
                print(f"    Messages: {len(topic.get('messages', []))}")
                print(f"    Top terms: {', '.join(topic.get('top_terms', [])[:3])}")
                print()
        except Exception as e:
            print(f"✗ KNN topic extraction failed: {e}")
        
        # Demo 3: Message classification
        print(f"=== Message Classification ===")
        topics_document = """
Available Topics:
1. Work/Business - Meetings, project updates, work-related communications
2. Finance/Billing - Invoices, payments, financial matters
3. Newsletter/Marketing - Newsletters, promotional content, updates
4. Personal - Personal communications, family, friends
"""
        
        try:
            classifications = llm_manager.classify_messages(messages, topics_document)
            print(f"✓ Classified {len(classifications)} messages")
            for classification in classifications:
                email_idx = classification.get('email_index', 0)
                topic = classification.get('topic', 'Unknown')
                confidence = classification.get('confidence', 0)
                print(f"  Email {email_idx}: {topic} (confidence: {confidence})")
        except Exception as e:
            print(f"✗ Classification failed: {e}")
        
        # Demo 4: General analysis
        print(f"\n=== General Analysis ===")
        try:
            analysis = llm_manager.analyze_messages(
                messages,
                task="Summarize the main themes and urgency levels of these emails",
                context="Daily email review for priority management"
            )
            print(f"✓ Analysis completed")
            print(f"Analysis result:\n{analysis}")
        except Exception as e:
            print(f"✗ Analysis failed: {e}")
        
        print(f"\n=== Advanced Demo Complete ===")


if __name__ == "__main__":
    demo_advanced_llm()
