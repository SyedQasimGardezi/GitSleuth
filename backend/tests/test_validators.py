"""Tests for validation utilities"""

import pytest
from utils.validators import URLValidator, TextValidator, SessionValidator, ConfigValidator
from utils.exceptions import ValidationError

class TestURLValidator:
    """Test URL validation"""
    
    def test_valid_github_urls(self):
        """Test valid GitHub URLs"""
        valid_urls = [
            "https://github.com/user/repo",
            "https://github.com/facebook/react",
            "https://github.com/microsoft/vscode",
            "https://github.com/user/repo-name",
            "https://github.com/user123/repo123"
        ]
        
        for url in valid_urls:
            result = URLValidator.validate_github_url(url)
            assert result == url
    
    def test_invalid_github_urls(self):
        """Test invalid GitHub URLs"""
        invalid_urls = [
            "https://gitlab.com/user/repo",
            "https://github.com/",
            "https://github.com/user",
            "https://github.com/user/",
            "not-a-url",
            "",
            "https://github.com/-user/repo",
            "https://github.com/user/-repo"
        ]
        
        for url in invalid_urls:
            with pytest.raises(ValidationError):
                URLValidator.validate_github_url(url)
    
    def test_url_normalization(self):
        """Test URL normalization"""
        test_cases = [
            ("github.com/user/repo", "https://github.com/user/repo"),
            ("http://github.com/user/repo", "https://github.com/user/repo"),
        ]
        
        for input_url, expected in test_cases:
            result = URLValidator.validate_github_url(input_url)
            assert result == expected

class TestTextValidator:
    """Test text validation"""
    
    def test_valid_questions(self):
        """Test valid questions"""
        valid_questions = [
            "What is this code doing?",
            "How does authentication work?",
            "Where is the main function?",
            "A" * 1000  # Max length
        ]
        
        for question in valid_questions:
            result = TextValidator.validate_question(question)
            assert result == question.strip()
    
    def test_invalid_questions(self):
        """Test invalid questions"""
        invalid_questions = [
            "",
            "   ",
            "A" * 1001,  # Too long
            "<script>alert('xss')</script>",
            "javascript:alert('xss')",
            "data:text/html,<script>alert('xss')</script>"
        ]
        
        for question in invalid_questions:
            with pytest.raises(ValidationError):
                TextValidator.validate_question(question)
    
    def test_valid_conversation_history(self):
        """Test valid conversation history"""
        valid_history = [
            {
                "role": "user",
                "content": "What is this code doing?"
            },
            {
                "role": "assistant",
                "content": "This code implements authentication."
            }
        ]
        
        result = TextValidator.validate_conversation_history(valid_history)
        assert result == valid_history
    
    def test_invalid_conversation_history(self):
        """Test invalid conversation history"""
        invalid_histories = [
            "not a list",
            [{"role": "user"}],  # Missing content
            [{"content": "test"}],  # Missing role
            [{"role": "invalid", "content": "test"}],  # Invalid role
            [{"role": "user", "content": ""}],  # Empty content
            [{"role": "user", "content": "test"}] * 51  # Too many messages
        ]
        
        for history in invalid_histories:
            with pytest.raises(ValidationError):
                TextValidator.validate_conversation_history(history)

class TestSessionValidator:
    """Test session validation"""
    
    def test_valid_session_ids(self):
        """Test valid session IDs"""
        valid_ids = [
            "123e4567-e89b-12d3-a456-426614174000",
            "00000000-0000-0000-0000-000000000000",
            "FFFFFFFF-FFFF-FFFF-FFFF-FFFFFFFFFFFF"
        ]
        
        for session_id in valid_ids:
            result = SessionValidator.validate_session_id(session_id)
            assert result == session_id
    
    def test_invalid_session_ids(self):
        """Test invalid session IDs"""
        invalid_ids = [
            "",
            "not-a-uuid",
            "123e4567-e89b-12d3-a456-42661417400",  # Too short
            "123e4567-e89b-12d3-a456-4266141740000",  # Too long
            "123e4567-e89b-12d3-a456-42661417400g"  # Invalid character
        ]
        
        for session_id in invalid_ids:
            with pytest.raises(ValidationError):
                SessionValidator.validate_session_id(session_id)

class TestConfigValidator:
    """Test configuration validation"""
    
    def test_valid_openai_key(self):
        """Test valid OpenAI API key"""
        valid_keys = [
            "sk-1234567890abcdef1234567890abcdef1234567890abcdef",
            "sk-" + "a" * 20
        ]
        
        for key in valid_keys:
            result = ConfigValidator.validate_openai_key(key)
            assert result == key
    
    def test_invalid_openai_key(self):
        """Test invalid OpenAI API key"""
        invalid_keys = [
            "",
            "not-an-openai-key",
            "sk-",
            "sk-123",  # Too short
            "pk-1234567890abcdef1234567890abcdef1234567890abcdef"  # Wrong prefix
        ]
        
        for key in invalid_keys:
            with pytest.raises(ValidationError):
                ConfigValidator.validate_openai_key(key)
    
    def test_valid_chunk_size(self):
        """Test valid chunk size"""
        valid_sizes = [100, 1000, 5000, 10000]
        
        for size in valid_sizes:
            result = ConfigValidator.validate_chunk_size(size)
            assert result == size
    
    def test_invalid_chunk_size(self):
        """Test invalid chunk size"""
        invalid_sizes = [99, 10001, "not-a-number", -1]
        
        for size in invalid_sizes:
            with pytest.raises(ValidationError):
                ConfigValidator.validate_chunk_size(size)
    
    def test_valid_chunk_overlap(self):
        """Test valid chunk overlap"""
        valid_overlaps = [(100, 200), (500, 1000), (0, 1000)]
        
        for overlap, chunk_size in valid_overlaps:
            result = ConfigValidator.validate_chunk_overlap(overlap, chunk_size)
            assert result == overlap
    
    def test_invalid_chunk_overlap(self):
        """Test invalid chunk overlap"""
        invalid_cases = [
            (-1, 1000),  # Negative
            (1000, 1000),  # Equal to chunk size
            (1001, 1000),  # Greater than chunk size
            ("not-a-number", 1000)  # Not a number
        ]
        
        for overlap, chunk_size in invalid_cases:
            with pytest.raises(ValidationError):
                ConfigValidator.validate_chunk_overlap(overlap, chunk_size)
