"""
HTML handling utilities for email processing.
"""
import re
from typing import Optional
from bs4 import BeautifulSoup

def html_to_text(html_content: str) -> str:
    """
    HTML to plain text converter using BeautifulSoup for robust parsing.
    
    Args:
        html_content: The HTML content to convert
        
    Returns:
        Plain text extracted from HTML with preserved structure
    """
    if not html_content:
        return ""
    
    # Use BeautifulSoup to parse the HTML with html5lib for better parsing
    # Fall back to html.parser if html5lib is not available
    try:
        soup = BeautifulSoup(html_content, 'html5lib')
    except ImportError:
        soup = BeautifulSoup(html_content, 'html.parser')
    
    # Remove script, style, head, and other non-content elements
    for element in soup(['script', 'style', 'head', 'meta', 'noscript', 'iframe']):
        element.decompose()
    
    # Replace <br> and <p> tags with newlines for better readability
    for br in soup.find_all(['br', 'p']):
        br.insert_after('\n')
    
    # Replace list items with formatted text
    for li in soup.find_all('li'):
        li.insert_before('• ')
    
    # Handle headings with emphasis
    for heading in soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6']):
        heading.insert_before('\n\n')
        heading.insert_after('\n')
    
    # Get the text content with preserved whitespace
    text = soup.get_text(separator=' ')
    
    # Clean up whitespace while preserving structure
    lines = [line.strip() for line in text.splitlines()]
    text = '\n'.join(line for line in lines if line)
    
    # Remove excessive newlines (more than 2 consecutive)
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    # Fix spacing issues
    text = re.sub(r' +', ' ', text)
    
    return text.strip()
