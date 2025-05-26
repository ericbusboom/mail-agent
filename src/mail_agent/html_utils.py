"""
HTML handling utilities for email processing.
"""
import re
from typing import Optional

def html_to_text(html_content: str) -> str:
    """
    Simple HTML to plain text converter. This is a basic implementation
    that doesn't require additional dependencies like BeautifulSoup.
    
    Args:
        html_content: The HTML content to convert
        
    Returns:
        Plain text extracted from HTML
    """
    if not html_content:
        return ""
    
    # Remove HTML tags, but keep their contents
    text = re.sub(r'<head.*?>.*?</head>', '', html_content, flags=re.DOTALL)
    text = re.sub(r'<style.*?>.*?</style>', '', text, flags=re.DOTALL)
    text = re.sub(r'<script.*?>.*?</script>', '', text, flags=re.DOTALL)
    
    # Replace common HTML entities
    entities = {
        '&nbsp;': ' ', '&lt;': '<', '&gt;': '>', '&amp;': '&',
        '&quot;': '"', '&apos;': "'", '&#39;': "'", '&ldquo;': '"', 
        '&rdquo;': '"', '&mdash;': '—', '&ndash;': '–', '&hellip;': '...'
    }
    for entity, replacement in entities.items():
        text = text.replace(entity, replacement)
        
    # Handle line breaks and paragraphs
    text = re.sub(r'<br\s*/?>|<p\s*.*?>', '\n', text)
    text = re.sub(r'</p>', '\n', text)
    
    # Remove all remaining tags
    text = re.sub(r'<.*?>', '', text)
    
    # Fix whitespace
    text = re.sub(r'\n\s*\n', '\n\n', text)  # Remove excess line breaks
    text = re.sub(r' +', ' ', text)  # Remove multiple spaces
    
    return text.strip()
