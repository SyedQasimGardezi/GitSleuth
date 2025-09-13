"""Input validation utilities"""

import re
import urllib.parse
from typing import Optional, Dict, Any
from utils.exceptions import ValidationError

class URLValidator:
    """GitHub URL validation"""
    
    GITHUB_PATTERN = re.compile(
        r'^https://github\.com/[a-zA-Z0-9][a-zA-Z0-9-_]*/[a-zA-Z0-9][a-zA-Z0-9-_]*/?$'
    )

    
    @classmethod
    def validate_github_url(cls, url: str) -> str:
        """Validate GitHub repository URL"""
        if not url:
            raise ValidationError("Repository URL cannot be empty")
        
        # Clean URL
        url = url.strip()
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        
        # Parse URL
        try:
            parsed = urllib.parse.urlparse(url)
        except Exception as e:
            raise ValidationError(f"Invalid URL format: {str(e)}")
        
        # Check if it's a GitHub URL
        if not cls.GITHUB_PATTERN.match(url):
            raise ValidationError(
                "Invalid GitHub repository URL. Expected format: https://github.com/username/repository"
            )
        
        return url

class TextValidator:
    """Text content validation"""
    
    MAX_QUESTION_LENGTH = 1000
    MAX_CONVERSATION_HISTORY = 50
    
    @classmethod
    def validate_question(cls, question: str) -> str:
        """Validate question text"""
        if not question:
            raise ValidationError("Question cannot be empty")
        
        question = question.strip()
        if len(question) > cls.MAX_QUESTION_LENGTH:
            raise ValidationError(
                f"Question too long. Maximum length is {cls.MAX_QUESTION_LENGTH} characters"
            )
        
        # Check for potentially harmful content
        if cls._contains_malicious_content(question):
            raise ValidationError("Question contains potentially harmful content")
        
        return question
    
    @classmethod
    def validate_conversation_history(cls, history: list) -> list:
        """Validate conversation history"""
        if not isinstance(history, list):
            raise ValidationError("Conversation history must be a list")
        
        if len(history) > cls.MAX_CONVERSATION_HISTORY:
            raise ValidationError(
                f"Conversation history too long. Maximum {cls.MAX_CONVERSATION_HISTORY} messages"
            )
        
        for i, message in enumerate(history):
            if not isinstance(message, dict):
                raise ValidationError(f"Message {i} must be a dictionary")
            
            required_fields = ['role', 'content']
            for field in required_fields:
                if field not in message:
                    raise ValidationError(f"Message {i} missing required field: {field}")
            
            if message['role'] not in ['user', 'assistant']:
                raise ValidationError(f"Message {i} has invalid role: {message['role']}")
            
            if not isinstance(message['content'], str) or not message['content'].strip():
                raise ValidationError(f"Message {i} content cannot be empty")
        
        return history
    
    @classmethod
    def _contains_malicious_content(cls, text: str) -> bool:
        """Check for potentially malicious content"""
        malicious_patterns = [
            r'<script.*?>.*?</script>',
            r'javascript:',
            r'data:text/html',
            r'vbscript:',
            r'onload\s*=',
            r'onerror\s*=',
        ]
        
        text_lower = text.lower()
        for pattern in malicious_patterns:
            if re.search(pattern, text_lower, re.IGNORECASE):
                return True
        
        return False

class SessionValidator:
    """Session validation"""
    
    UUID_PATTERN = re.compile(
        r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$',
        re.IGNORECASE
    )
    
    @classmethod
    def validate_session_id(cls, session_id: str) -> str:
        """Validate session ID format"""
        if not session_id:
            raise ValidationError("Session ID cannot be empty")
        
        session_id = session_id.strip()
        if not cls.UUID_PATTERN.match(session_id):
            raise ValidationError("Invalid session ID format")
        
        return session_id

class ConfigValidator:
    """Configuration validation"""
    
    @classmethod
    def validate_openai_key(cls, api_key: str) -> str:
        """Validate OpenAI API key format"""
        if not api_key:
            raise ValidationError("OpenAI API key is required")
        
        if not api_key.startswith('sk-'):
            raise ValidationError("Invalid OpenAI API key format")
        
        if len(api_key) < 20:
            raise ValidationError("OpenAI API key too short")
        
        return api_key
    
    @classmethod
    def validate_chunk_size(cls, chunk_size: int) -> int:
        """Validate chunk size"""
        if not isinstance(chunk_size, int):
            raise ValidationError("Chunk size must be an integer")
        
        if chunk_size < 100:
            raise ValidationError("Chunk size too small (minimum 100)")
        
        if chunk_size > 10000:
            raise ValidationError("Chunk size too large (maximum 10000)")
        
        return chunk_size
    
    @classmethod
    def validate_chunk_overlap(cls, chunk_overlap: int, chunk_size: int) -> int:
        """Validate chunk overlap"""
        if not isinstance(chunk_overlap, int):
            raise ValidationError("Chunk overlap must be an integer")
        
        if chunk_overlap < 0:
            raise ValidationError("Chunk overlap cannot be negative")
        
        if chunk_overlap >= chunk_size:
            raise ValidationError("Chunk overlap must be less than chunk size")
        
        return chunk_overlap
