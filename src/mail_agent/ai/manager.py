"""
LLM Manager for Mail Agent AI functionality.
"""
import json
import logging
import os
from pathlib import Path
from typing import List, Dict, Any, Optional, Union
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.neighbors import NearestNeighbors
from sklearn.cluster import KMeans

from langchain.prompts import PromptTemplate
from langchain.schema import BaseMessage, HumanMessage, SystemMessage

# Try to import LLM providers, but gracefully handle missing ones
try:
    from langchain_openai import ChatOpenAI
except ImportError:
    ChatOpenAI = None

try:
    from langchain_anthropic import ChatAnthropic
except ImportError:
    ChatAnthropic = None

try:
    from langchain_google_genai import ChatGoogleGenerativeAI
except ImportError:
    ChatGoogleGenerativeAI = None

from mail_agent.gmail import GmailMessage

logger = logging.getLogger(__name__)


class LLMManager:
    """
    Manager class for LLM operations in Mail Agent.
    
    Handles:
    - LLM client creation based on configuration
    - Prompt template loading and rendering
    - Email analysis and classification
    - Topic extraction using KNN and clustering
    """
    
    def __init__(self, app):
        """
        Initialize LLMManager with MailAgentApp instance.
        
        Args:
            app: MailAgentApp instance
        """
        self.app = app
        self.config = app.app_config
        self._client = None
        self._prompts = {}
        self._load_prompts()
    
    @property
    def client(self):
        """Get or create LLM client based on configuration."""
        if self._client is None:
            self._client = self._create_client()
        return self._client
    
    def _create_client(self):
        """
        Create LLM client based on configuration.
        
        Returns:
            LLM client instance
        """
        provider = self.config.get('LLM_PROVIDER', 'openai').lower()
        model_name = self.config.get('LLM_NAME', 'gpt-3.5-turbo')
        
        logger.info(f"Creating LLM client: provider={provider}, model={model_name}")
        
        try:
            if provider == 'openai' and ChatOpenAI:
                api_key = self.config.get('OPENAI_API_KEY')
                if not api_key:
                    raise ValueError("OPENAI_API_KEY not found in configuration")
                os.environ['OPENAI_API_KEY'] = api_key
                return ChatOpenAI(model=model_name, temperature=0.1)
            
            elif provider == 'anthropic' and ChatAnthropic:
                api_key = self.config.get('ANTHROPIC_API_KEY')
                if not api_key:
                    raise ValueError("ANTHROPIC_API_KEY not found in configuration")
                os.environ['ANTHROPIC_API_KEY'] = api_key
                return ChatAnthropic(
                    model_name=model_name,
                    timeout=60,
                    stop=None
                )
            
            elif provider == 'google' and ChatGoogleGenerativeAI:
                api_key = self.config.get('GOOGLE_AI_API_KEY')
                if not api_key:
                    raise ValueError("GOOGLE_AI_API_KEY not found in configuration")
                os.environ['GOOGLE_API_KEY'] = api_key
                return ChatGoogleGenerativeAI(model=model_name, temperature=0.1)
            
            else:
                logger.warning(f"Provider {provider} not available or not supported")
                return self._create_mock_client()
                
        except Exception as e:
            logger.warning(f"Failed to create {provider} client: {e}")
            return self._create_mock_client()
    
    def _create_mock_client(self):
        """Create a mock client for development/testing."""
        class MockResponse:
            def __init__(self, content: str):
                self.content = content
        
        class MockClient:
            def invoke(self, messages):
                return MockResponse("Mock response: This is a placeholder response from the mock LLM client.")
        
        return MockClient()
    
    def _load_prompts(self):
        """Load all prompt templates from the prompts directory."""
        prompts_dir = Path(__file__).parent / "prompts"
        
        for prompt_file in prompts_dir.glob("*.txt"):
            template_name = prompt_file.stem
            try:
                with open(prompt_file, 'r', encoding='utf-8') as f:
                    template_content = f.read()
                
                # Create PromptTemplate with Jinja2 formatting
                self._prompts[template_name] = PromptTemplate(
                    template=template_content,
                    input_variables=self._extract_template_variables(template_content),
                    template_format="jinja2"
                )
                logger.debug(f"Loaded prompt template: {template_name}")
                
            except Exception as e:
                logger.error(f"Failed to load prompt template {template_name}: {e}")
    
    def _extract_template_variables(self, template_content: str) -> List[str]:
        """
        Extract variable names from Jinja2 template content.
        
        Args:
            template_content: The template content string
            
        Returns:
            List of variable names found in the template
        """
        import re
        
        # Find all Jinja2 variables: {{ variable }} and {% for variable in ... %}
        variable_pattern = r'\{\{\s*([a-zA-Z_][a-zA-Z0-9_]*)'
        for_pattern = r'\{\%\s*for\s+[a-zA-Z_][a-zA-Z0-9_]*\s+in\s+([a-zA-Z_][a-zA-Z0-9_]*)'
        
        variables = set()
        variables.update(re.findall(variable_pattern, template_content))
        variables.update(re.findall(for_pattern, template_content))
        
        # Filter out common Jinja2 built-ins
        builtin_vars = {'loop', 'length'}
        variables = {var for var in variables if var not in builtin_vars}
        
        return list(variables)
    
    def get_prompt_template(self, template_name: str) -> PromptTemplate:
        """
        Get a loaded prompt template by name.
        
        Args:
            template_name: Name of the template (without .txt extension)
            
        Returns:
            PromptTemplate instance
        """
        if template_name not in self._prompts:
            raise ValueError(f"Prompt template '{template_name}' not found")
        return self._prompts[template_name]
    
    def create_document(self, messages: List[GmailMessage], template_name: str, **kwargs) -> str:
        """
        Create a document from email messages using a prompt template.
        
        Args:
            messages: List of GmailMessage objects
            template_name: Name of the prompt template to use
            **kwargs: Additional variables to pass to the template
            
        Returns:
            Rendered document string
        """
        template = self.get_prompt_template(template_name)
        
        # Prepare template variables
        template_vars = {
            'messages': messages,
            **kwargs
        }
        
        try:
            document = template.format(**template_vars)
            logger.debug(f"Created document using template '{template_name}' with {len(messages)} messages")
            return document
        except Exception as e:
            logger.error(f"Failed to create document with template '{template_name}': {e}")
            raise
    
    def send_request(self, prompt: str, **kwargs) -> str:
        """
        Send a request to the LLM.
        
        Args:
            prompt: The prompt to send
            **kwargs: Additional parameters for the LLM
            
        Returns:
            LLM response string
        """
        try:
            # Use the client to get response
            response = self.client.invoke(prompt)
            content = response.content
            
            # Handle different response types
            if isinstance(content, str):
                return content
            elif isinstance(content, list):
                # Join list elements if it's a list
                return " ".join(str(item) for item in content)
            else:
                return str(content)
                
        except Exception as e:
            logger.error(f"Failed to send LLM request: {e}")
            raise
    
    def extract_topics_knn(self, messages: List[GmailMessage], n_topics: int = 5) -> List[Dict[str, Any]]:
        """
        Extract topics from email messages using KNN clustering.
        
        Args:
            messages: List of GmailMessage objects
            n_topics: Number of topics to extract
            
        Returns:
            List of topic dictionaries with names, descriptions, and related messages
        """
        if len(messages) < n_topics:
            logger.warning(f"Not enough messages ({len(messages)}) for {n_topics} topics")
            n_topics = max(1, len(messages))
        
        # Extract text content from messages
        texts = []
        for msg in messages:
            # Combine subject and body for better clustering
            content = f"{msg.subject} {msg.body_text or ''}"
            texts.append(content)
        
        # Vectorize the text using TF-IDF
        vectorizer = TfidfVectorizer(
            max_features=1000,
            stop_words='english',
            ngram_range=(1, 2)
        )
        
        try:
            tfidf_matrix = vectorizer.fit_transform(texts)
        except ValueError as e:
            logger.error(f"Failed to vectorize texts: {e}")
            return []
        
        # Use KMeans clustering to find topics
        kmeans = KMeans(n_clusters=n_topics, random_state=42, n_init=10)
        cluster_labels = kmeans.fit_predict(tfidf_matrix)
        
        # Get feature names for interpretation
        feature_names = vectorizer.get_feature_names_out()
        
        # Extract topics from clusters
        topics = []
        for cluster_id in range(n_topics):
            # Get messages in this cluster
            cluster_messages = [messages[i] for i, label in enumerate(cluster_labels) if label == cluster_id]
            
            if not cluster_messages:
                continue
            
            # Get top terms for this cluster
            cluster_center = kmeans.cluster_centers_[cluster_id]
            top_indices = cluster_center.argsort()[-10:][::-1]  # Top 10 terms
            top_terms = [str(feature_names[i]) for i in top_indices]
            
            # Create topic name from top terms
            topic_name = " ".join(top_terms[:3]).title()
            
            topics.append({
                'name': topic_name,
                'description': f"Topic derived from {len(cluster_messages)} emails with key terms: {', '.join(top_terms[:5])}",
                'messages': cluster_messages,
                'message_indices': [i for i, label in enumerate(cluster_labels) if label == cluster_id],
                'top_terms': top_terms
            })
        
        logger.info(f"Extracted {len(topics)} topics using KNN clustering")
        return topics
    
    def classify_messages(self, messages: List[GmailMessage], topics_document: str) -> List[Dict[str, Any]]:
        """
        Classify email messages based on provided topic definitions.
        
        Args:
            messages: List of GmailMessage objects to classify
            topics_document: Document describing available topics
            
        Returns:
            List of classification results
        """
        try:
            # Create classification prompt
            prompt = self.create_document(
                messages=messages,
                template_name="email_classification",
                topics_document=topics_document
            )
            
            # Send to LLM
            response = self.send_request(prompt)
            
            # Parse JSON response
            classification_data = json.loads(response)
            classifications = classification_data.get('classifications', [])
            
            logger.info(f"Classified {len(classifications)} messages")
            return classifications
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse classification response as JSON: {e}")
            return []
        except Exception as e:
            logger.error(f"Failed to classify messages: {e}")
            return []
    
    def extract_topics_llm(self, messages: List[GmailMessage]) -> List[Dict[str, Any]]:
        """
        Extract topics from email messages using LLM analysis.
        
        Args:
            messages: List of GmailMessage objects
            
        Returns:
            List of topic dictionaries
        """
        try:
            # Create topic extraction prompt
            prompt = self.create_document(
                messages=messages,
                template_name="topic_extraction"
            )
            
            # Send to LLM
            response = self.send_request(prompt)
            
            # Parse JSON response
            topic_data = json.loads(response)
            topics = topic_data.get('topics', [])
            
            logger.info(f"Extracted {len(topics)} topics using LLM analysis")
            return topics
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse topic extraction response as JSON: {e}")
            return []
        except Exception as e:
            logger.error(f"Failed to extract topics: {e}")
            return []
    
    def analyze_messages(self, messages: List[GmailMessage], task: str, context: str = "") -> str:
        """
        General purpose message analysis using LLM.
        
        Args:
            messages: List of GmailMessage objects
            task: Description of the analysis task
            context: Additional context for the analysis
            
        Returns:
            Analysis result string
        """
        try:
            # Create general analysis prompt
            prompt = self.create_document(
                messages=messages,
                template_name="general_analysis",
                task=task,
                context=context
            )
            
            # Send to LLM
            response = self.send_request(prompt)
            
            logger.info(f"Completed analysis task: {task}")
            return response
            
        except Exception as e:
            logger.error(f"Failed to analyze messages: {e}")
            return f"Analysis failed: {str(e)}"
    
    def get_available_templates(self) -> List[str]:
        """Get list of available prompt template names."""
        return list(self._prompts.keys())
    
    def get_client_info(self) -> Dict[str, Any]:
        """Get information about the current LLM client."""
        provider = self.config.get('LLM_PROVIDER', 'openai').lower()
        model_name = self.config.get('LLM_NAME', 'gpt-3.5-turbo')
        
        return {
            'provider': provider,
            'model': model_name,
            'client_type': type(self.client).__name__,
            'is_mock': isinstance(self.client, type(self._create_mock_client()))
        }
    
    def reload_prompts(self):
        """Reload all prompt templates from disk."""
        self._prompts.clear()
        self._load_prompts()
        logger.info(f"Reloaded {len(self._prompts)} prompt templates")
    
    def batch_classify_messages(self, messages: List[GmailMessage], topics_document: str, 
                              batch_size: int = 10) -> List[Dict[str, Any]]:
        """
        Classify messages in batches for better performance with large datasets.
        
        Args:
            messages: List of GmailMessage objects to classify
            topics_document: Document describing available topics
            batch_size: Number of messages to process in each batch
            
        Returns:
            List of classification results
        """
        all_classifications = []
        
        for i in range(0, len(messages), batch_size):
            batch = messages[i:i + batch_size]
            logger.info(f"Processing batch {i//batch_size + 1}: messages {i+1}-{min(i+batch_size, len(messages))}")
            
            try:
                batch_results = self.classify_messages(batch, topics_document)
                
                # Adjust email indices to be relative to the full list
                for result in batch_results:
                    if 'email_index' in result:
                        result['email_index'] += i
                
                all_classifications.extend(batch_results)
                
            except Exception as e:
                logger.error(f"Failed to process batch {i//batch_size + 1}: {e}")
                continue
        
        return all_classifications
    
    def validate_template(self, template_name: str) -> Dict[str, Any]:
        """
        Validate a prompt template and return information about it.
        
        Args:
            template_name: Name of the template to validate
            
        Returns:
            Dictionary with validation results
        """
        if template_name not in self._prompts:
            return {
                'valid': False,
                'error': f"Template '{template_name}' not found",
                'available': list(self._prompts.keys())
            }
        
        template = self._prompts[template_name]
        
        try:
            # Test template with minimal data
            test_result = template.format(
                messages=[],
                task="test",
                context="test",
                topics_document="test"
            )
            
            return {
                'valid': True,
                'input_variables': template.input_variables,
                'template_format': template.template_format,
                'length': len(template.template)
            }
            
        except Exception as e:
            return {
                'valid': False,
                'error': str(e),
                'input_variables': getattr(template, 'input_variables', [])
            }