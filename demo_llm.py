#!/usr/bin/env python3
"""
Example script demonstrating LLMManager usage.
"""

import sys
from pathlib import Path

# Add the src directory to the path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from mail_agent.app import MailAgentApp
from mail_agent.gmail import Gmail


def demo_llm_manager():
    """Demonstrate LLMManager functionality."""
    
    # Create app instance
    app = MailAgentApp(__name__)
    
    with app.app_context():
        print("=== LLMManager Demo ===")
        
        # Check if LLM Manager is available
        if hasattr(app, 'llm_manager'):
            llm_manager = app.llm_manager
            print(f"✓ LLMManager initialized successfully")
            
            # Show available prompt templates
            print(f"\nAvailable prompt templates:")
            for template_name in llm_manager._prompts.keys():
                print(f"  - {template_name}")
            
            # Create some sample messages for testing
            sample_messages = []
            
            # Example 1: Create a document (without actual messages)
            print(f"\n=== Document Creation Demo ===")
            try:
                if 'general_analysis' in llm_manager._prompts:
                    document = llm_manager.create_document(
                        messages=sample_messages,
                        template_name='general_analysis',
                        task="Analyze email patterns",
                        context="Demo context"
                    )
                    print(f"✓ Document created successfully")
                    print(f"Document preview: {document[:200]}...")
                else:
                    print("⚠ general_analysis template not found")
            except Exception as e:
                print(f"✗ Document creation failed: {e}")
            
            # Example 2: Test LLM request (with mock client)
            print(f"\n=== LLM Request Demo ===")
            try:
                response = llm_manager.send_request("Hello, this is a test prompt.")
                print(f"✓ LLM request successful")
                print(f"Response: {response}")
            except Exception as e:
                print(f"✗ LLM request failed: {e}")
            
            # Example 3: Topic extraction with KNN (without real messages)
            print(f"\n=== Topic Extraction Demo ===")
            print("Note: Topic extraction requires actual email messages")
            print("This demo would extract topics using KNN clustering from email content")
            
        else:
            print("✗ LLMManager not found in app")
    
    print(f"\n=== Demo Complete ===")


if __name__ == "__main__":
    demo_llm_manager()
